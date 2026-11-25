"""Offline transport, pairing, failure and analysis controls; no the Mac Studio access."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from depth_retrieval import ARCHIVE, HERE, LABS, LANES, MANIFEST, PASSES, batch, eligible, select, validate
from protocol import read
from analyze_depth_retrieval import analyze, contrast, load, plots, wilson

spec = importlib.util.spec_from_file_location('depth_stub', LABS/'tests/stub_server.py')
stub_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stub_module)


class DepthRetrieval(unittest.TestCase):
    def test_fixed_balanced_manifest(self):
        manifest = read(MANIFEST)
        self.assertEqual(manifest, select(150))
        self.assertEqual(len(validate(manifest)),150)
        self.assertEqual(len(eligible()),212)
        self.assertEqual(len(manifest['strata']),7)
        self.assertIn('abstention',manifest['strata'])
        self.assertEqual(len(manifest['input_sha256']),450)
        manifest['questions'][0]['question_type'] = 'invented'
        with self.assertRaisesRegex(ValueError,'type'):
            validate(manifest)

    def test_all_twelve_cells_resume_failures_and_analysis_cli(self):
        with tempfile.TemporaryDirectory() as tmp, stub_module.Stub() as stub:
            root = Path(tmp)
            manifest = select(3)
            path = root/'selection.json'
            path.write_text(json.dumps(manifest))
            hook_count = root/'hooks'
            hook = 'echo restart >> '+str(hook_count)
            for depth in PASSES:
                batch(depth,path,root,'stub-reader',stub.url,hook,5,stub.url)
                run = root/f'varloop-p{depth}'
                state = read(run/'longmemeval/summary.json')
                self.assertEqual(state['completed'],9)
                self.assertEqual(set(state['systems']),set(LANES))
                self.assertFalse((run/'locomo').exists())
                for lane in LANES:
                    self.assertEqual({p.stem for p in (run/'longmemeval/items'/lane).glob('*.json')},
                                     {q['question_id'] for q in manifest['questions']})
                    self.assertEqual(state['systems'][lane]['skipped'],0)
                before = len(stub.calls)
                batch(depth,path,root,'stub-reader',stub.url,hook,5,stub.url)
                self.assertEqual(len(stub.calls),before)
            self.assertEqual(len(hook_count.read_text().splitlines()),4)
            reader = [c for c in stub.calls if c['model']=='stub-reader']
            self.assertEqual(len(reader),36)
            for c in reader:
                self.assertEqual(c['thinking_budget'],0)
                self.assertFalse(c['chat_template_kwargs']['enable_thinking'])
            self.assertEqual(len(stub.calls),144)
            cells = load(root,manifest)
            self.assertEqual(len(cells),12)
            subprocess.run([sys.executable,str(HERE/'analyze_depth_retrieval.py'),
                            '--results',str(root),'--selection',str(path),'--output',str(root/'analysis'),
                            '--bootstrap','200'],check=True,capture_output=True,text=True)
            report = read(root/'analysis/analysis.json')
            self.assertEqual(report['primary_interaction']['difference'],0)
            self.assertTrue(all(r['match_within_5pp'] for r in report['iso_accuracy']))
            for svg in (root/'analysis').glob('*.svg'):
                ET.parse(svg)
            # A missing cell must fail, rather than silently changing the paired denominator.
            missing = root/'varloop-p5/longmemeval/items'/LANES[0]/(manifest['questions'][0]['question_id']+'.json')
            missing.unlink()
            with self.assertRaisesRegex(ValueError,'Incomplete'):
                load(root,manifest)
            with self.assertRaises(subprocess.CalledProcessError):
                batch(1,path,root/'failed','stub-reader',stub.url,'exit 7',5,stub.url)
            self.assertEqual(read(root/'failed/varloop-p1/longmemeval/summary.json')['completed'],5)
            with self.assertRaisesRegex(RuntimeError,'settings'):
                batch(1,path,root,'different-model',stub.url,hook,5,stub.url)

    def test_fixture_statistics_and_signs(self):
        fixture = read(HERE/'fixtures/depth-retrieval.json')
        cells = {(int(d),lane):values for d,lanes in fixture['cells'].items() for lane,values in lanes.items()}
        result = analyze(cells,fixture['questions'],500)
        self.assertEqual(len(result['cells']),12)
        self.assertEqual(len(result['depth_differences']),18)
        self.assertEqual(len(result['retrieval_differences']),12)
        self.assertEqual(len(result['iso_accuracy']),16)
        self.assertEqual(len(result['per_type']['five_groups']),5)
        self.assertEqual(result['primary_interaction']['difference'],1)
        self.assertEqual(result['primary_interaction']['ci95'],[1,1])
        self.assertEqual(result['preregistered_classification'],'depth substitutes for retrieval')
        # Known Wilson control, and contrast CI must use paired differences, not two marginals.
        self.assertAlmostEqual(wilson(5,10)[0],.2365930905)
        paired = contrast([0]*20,['type']*20,200)
        self.assertEqual(paired['ci95'],[0,0])
        mixed = contrast([-1,1]*20,['type']*40,500)
        self.assertLess(mixed['ci95'][0],0)
        self.assertGreater(mixed['ci95'][1],0)
        # Non-significance alone never establishes equivalence.
        varied = {key:[i%2 for i in range(40)] for key in cells}
        varied[1,LANES[1]] = [1-i%2 for i in range(40)]
        uncertain = analyze(varied,fixture['questions'],500)
        self.assertFalse(next(r for r in uncertain['iso_accuracy'] if r['oracle_depth']==1 and r['bm25_depth']==1)['match_within_5pp'])
        with tempfile.TemporaryDirectory() as tmp:
            plots(result,Path(tmp))
            for svg in Path(tmp).glob('*.svg'):
                ET.parse(svg)


if __name__ == '__main__':
    unittest.main()
