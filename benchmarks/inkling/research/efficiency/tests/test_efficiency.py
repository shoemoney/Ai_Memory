import copy
import contextlib
import io
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import re
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
FIX = HERE / 'tests/fixtures'


def module(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + '.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


power = module('power')
accept = module('accept')
instrument = module('instrument_mtp')


class EnergyTests(unittest.TestCase):
    def test_recorded_mac27_plists_units_and_intervals(self):
        frames = re.findall(rb'<\?xml.*?</plist>', (FIX / 'power-probe.plist').read_bytes(), re.S)
        self.assertEqual(len(frames), 10)
        samples, t = [], 0.0
        for frame in frames:
            r = plistlib.loads(frame)
            t += r['elapsed_ns'] / 1e9
            samples.append(dict(r, end=t))
        self.assertAlmostEqual(power.watts(samples[0]), 25.72119, places=5)
        measured = power.integrate(samples, 0, t)
        self.assertAlmostEqual(measured['covered_seconds'], t)
        # Independent oracle: the actual plist supplies mJ counters.
        expected = sum(s['processor']['cpu_energy'] + s['processor']['gpu_energy'] +
                       s['processor']['ane_energy'] for s in samples) / 1000
        self.assertAlmostEqual(measured['joules'], expected, delta=0.04)
        self.assertGreater(measured['variance_watts2'], 0)

    def test_clipping_baseline_negative_net_zero_correct(self):
        samples = [dict(end=i + 1, elapsed_ns=10**9,
                        processor=dict(cpu_power=1000, gpu_power=w-1000, ane_power=0, combined_power=w))
                   for i, w in enumerate([10000, 20000, 5000, 5000])]
        joined = dict(requests=2, answer_requests=1, scored_items=1, correct_answers=0)
        r = power.report(samples, (0, 2), (2.25, 3.75), joined)
        self.assertEqual(r['benchmark']['joules'], 7.5)
        self.assertEqual(r['baseline']['mean_watts'], 15)
        self.assertEqual(r['baseline']['variance_watts2'], 25)
        self.assertEqual(r['net_joules'], -15)
        self.assertEqual(r['joules_per_request'], -7.5)
        self.assertIsNone(r['joules_per_correct_answer'])

    def test_missing_samples_schema_change_fail(self):
        with self.assertRaises(ValueError):
            power.integrate([], 0, 1)
        with self.assertRaises(ValueError):
            power.watts(dict(processor=dict(cpu_power=1000,gpu_power=1000,ane_power=0,combined_power=4000)))

    def test_join_only_new_or_changed_items_and_actual_requests(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            power.write(root/'items/lane/old.json',dict(status='scored',correct=True))
            before = power.snapshot(root)
            power.write(root/'items/lane/new.json',dict(status='scored',correct=False,item_id='new',lane='lane'))
            power.write(root/'items/lane/skip.json',dict(status='context-does-not-fit'))
            power.write(root/'raw/lane/new/answer-1.json',dict(request={},response={}))
            power.write(root/'raw/lane/new/judge-1.json',dict(request={},response={}))
            power.write(root/'raw/lane/new/judge-2.error.json',dict(request={},error='failed'))
            r = power.joined_items(root,before)
            self.assertEqual(r['scored_items'],1)
            self.assertEqual(r['correct_answers'],0)
            self.assertEqual((r['requests'],r['answer_requests'],r['judge_requests']),(2,1,1))
            self.assertEqual(len(r['items']),2)

    def test_remote_parser_handles_recorded_nul_separated_stream(self):
        fake = SimpleNamespace(stdout=io.BytesIO((FIX/'power-probe.plist').read_bytes()),
                               terminate=lambda:None, wait=lambda **kw:0, kill=lambda:None)
        output=io.StringIO()
        with patch('subprocess.Popen',return_value=fake), patch('signal.signal'), \
             patch('sys.stdin',SimpleNamespace(buffer=io.BytesIO())), contextlib.redirect_stdout(output):
            exec(compile(power.REMOTE,'remote_sampler','exec'),{})
        records=[json.loads(line) for line in output.getvalue().splitlines()]
        self.assertIn('ready',records[0])
        self.assertEqual(len(records),11)
        self.assertAlmostEqual(power.watts(records[1]),25.72119)

    def test_remote_sampler_compiles(self):
        compile(power.REMOTE,'remote_sampler','exec')


class AcceptanceTests(unittest.TestCase):
    def test_disjoint_log_segments_weighted_acceptance(self):
        r = accept.parse_stats((FIX/'mtp.log').read_text())
        self.assertEqual((r['accepted'],r['proposed']), (6,11))
        self.assertAlmostEqual(r['acceptance_rate'],6/11)
        self.assertEqual(r['upstream_evaluated'],8)
        self.assertEqual(r['copy_proposed'],4)

    def test_missing_telemetry_is_unknown(self):
        self.assertIsNone(accept.parse_stats('ordinary log')['acceptance_rate'])
        r=accept.parse_stats('MTP[0] finish=stop tokens=3 accept=1/2 (50.0%)')
        self.assertIsNone(r['proposed'])
        self.assertEqual(r['upstream_evaluated'],2)
        with self.assertRaises(ValueError):
            accept.parse_stats('EFFICIENCY_MTP[0] finish=stop accepted=3 proposed=2 copy_accepted=0 copy_proposed=0')

    def test_settings_must_match(self):
        good={'models':{'m':{'mtp_enabled':True}}}
        self.assertTrue(accept.checked_settings(good,'m','on')['mtp_enabled'])
        for model,mode in [('other','on'),('m','off')]:
            with self.assertRaises(ValueError): accept.checked_settings(good,model,mode)
        good['models']['m']['dflash_enabled']=True
        with self.assertRaises(ValueError): accept.checked_settings(good,'m','on')

    def test_recorded_response_throughput_not_average_rates(self):
        response=json.loads((FIX/'response.json').read_text())
        # Recorded smoke API response may be wrapped by infra's recorder.
        response=response.get('response',response)
        rows=[dict(seconds=2,response=copy.deepcopy(response),stats=accept.parse_stats((FIX/'mtp.log').read_text())) for _ in range(2)]
        for row in rows: row['response']['usage']['generation_duration']=1
        r=accept.summarize(rows,'on')
        tokens=response['usage']['completion_tokens']
        self.assertEqual(r['generation_tokens_per_second'],tokens)
        self.assertEqual(r['end_to_end_tokens_per_second'],tokens/2)
        self.assertEqual(r['proposed'],22)
        self.assertAlmostEqual(r['acceptance_rate'],6/11)

    def test_mode_runner_replays_recorded_response_and_log_join(self):
        response=json.loads((FIX/'response.json').read_text())
        response=response.get('response',response)
        log=(FIX/'mtp.log').read_text()
        prompts=json.loads((HERE/'prompts.json').read_text())['prompts'][-2:]
        with tempfile.TemporaryDirectory() as d:
            a=SimpleNamespace(model='m',configure_hook=None,out=Path(d),settings_command='settings',
                              log_command='log',base_url='http://unused',timeout=1,max_tokens=384)
            outputs=[json.dumps({'models':{'m':{'mtp_enabled':True}}}),'old', 'old'+log,
                     'old'+log,'old'+log+log]
            with patch.object(accept,'capture',side_effect=outputs), \
                 patch.object(accept,'request',return_value=response) as transport:
                result=accept.run_mode(a,prompts,'on')
            self.assertEqual(result['n'],2)
            self.assertEqual(result['proposed'],22)
            self.assertEqual(result['telemetry_requests'],2)
            self.assertEqual(transport.call_count,3)  # warmup plus two measured prompts
            for call in transport.call_args_list:
                body=call.args[1]
                self.assertEqual(body['thinking_budget'],0)
                self.assertFalse(body['chat_template_kwargs']['enable_thinking'])
                self.assertEqual(body['temperature'],0)
            self.assertTrue((Path(d)/'on/items'/ (prompts[0]['id']+'.json')).exists())

    def test_fixed_fifty_prompts(self):
        prompts=json.loads((HERE/'prompts.json').read_text())['prompts']
        self.assertEqual(len(prompts),50)
        self.assertEqual(len({r['id'] for r in prompts}),50)
        self.assertEqual(sum(r['kind']=='general' for r in prompts),25)
        self.assertEqual(sum(r['kind']=='longmemeval' for r in prompts),13)
        self.assertEqual(sum(r['kind']=='locomo' for r in prompts),12)

    def test_instrumentation_counts_rejected_suffix_without_changing_accepts(self):
        # Replay the recorded upstream stats block in a tiny host function.
        stats_block=(FIX/'upstream-stats.txt').read_text()
        source=('def cycle(state,copy_cycle,k,m,depth):\n'+stats_block+
                '\ndef log(stats,uid,finish_reason):\n'+instrument.LOG_ANCHOR).encode()
        with patch.object(instrument,'EXPECTED',hashlib.sha256(source).hexdigest()):
            modified=instrument.instrument(source)
            scope={}
            exec(compile(modified,'test','exec'),scope)
            stats=SimpleNamespace(cycles=0,copy_cycles=0,copy_drafted=0,copy_accepted=0,
                                  depth_drafted=[],depth_accepted=[],accepts=0,rejects=0,sample_ms=0)
            state=SimpleNamespace(stats=stats,depth=5)
            # The retained block references timers after counters; provide deterministic values.
            scope.update(time=SimpleNamespace(perf_counter=lambda:0),t0=0)
            scope['cycle'](state,False,5,2,5)
            self.assertEqual(stats.efficiency_proposed,5)
            self.assertEqual(stats.accepts,2)
            self.assertEqual(sum(stats.depth_drafted),3)
        with self.assertRaises(ValueError): instrument.instrument(b'wrong upstream source')


if __name__=='__main__':
    unittest.main()
