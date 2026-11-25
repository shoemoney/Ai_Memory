"""Real labs traffic through a loopback stub; no Mac, models, or network downloads."""
import ast
from collections import Counter
from dataclasses import dataclass
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import subprocess
import socket
import sys
import tempfile
import unittest

from protocol import HERE, LABS, batch, read, selection
from remote import model_view, owns_server, stop
from verify_source import verify

spec = importlib.util.spec_from_file_location('memory_loop_stub', LABS / 'tests/stub_server.py')
stub_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stub_module)


class Offline(unittest.TestCase):
    def test_source_verification_detects_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'weight').write_bytes(b'ab')
            (root / 'config').write_bytes(b'{}')
            evidence = {'model_revision':'fixture', 'files':[
                {'rfilename':'weight','size':2,'lfs':{'sha256':hashlib.sha256(b'ab').hexdigest()}},
                {'rfilename':'config','size':2,'blobId':hashlib.sha1(b'blob 2\0{}').hexdigest()}]}
            self.assertEqual(len(verify(root,evidence)['files']),2)
            (root / 'weight').write_bytes(b'cd')
            with self.assertRaisesRegex(RuntimeError,'Hash mismatch'):
                verify(root,evidence)
            (root / 'weight').write_bytes(b'abc')
            with self.assertRaisesRegex(RuntimeError,'incorrect size'):
                verify(root,evidence)

    def test_fixed_selection(self):
        self.assertEqual(read(HERE / 'selection.json'), selection())
        self.assertEqual(len(selection()['longmemeval']), 48)
        self.assertEqual(len(selection()['locomo']), 24)
        self.assertEqual({q[:3] for q in selection()['locomo']}, {'c00', 'c01', 'c03'})

    def test_config_views(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / 'source'
            src.mkdir()
            original = {'model_type':'inkling2_loop', 'text_config': {'loop_config':
                {'core_start':6,'core_end':18,'num_passes':3,'is_varloop':True}}, 'mtp_config': {'test':True}}
            (src / 'config.json').write_text(json.dumps(original))
            (src / 'model.safetensors').write_bytes(b'fixture')
            (src / 'mtp.safetensors').write_bytes(b'draft')
            for passes in (1,2,3,5):
                view = root / f'p{passes}'
                model_view(src, view, passes)
                config = read(view / 'config.json')
                self.assertEqual(config['text_config']['loop_num_passes'], passes)
                self.assertEqual(config['text_config']['loop_config']['num_passes'], passes)
                self.assertNotIn('mtp_config', config)
                self.assertFalse((view / 'mtp.safetensors').exists())
                self.assertTrue((view / 'model.safetensors').is_symlink())
            self.assertEqual(read(src / 'config.json'), original)
            original['text_config']['loop_config']['is_varloop'] = False
            (src / 'config.json').write_text(json.dumps(original))
            with self.assertRaises(ValueError):
                model_view(src, root / 'wrong-model', 3)

    def test_native_schedule(self):
        source = Path(os.environ.get('OMLX_SOURCE', '/tmp/memory-loops-omlx-083'))
        path = source / 'omlx/patches/inkling2/model.py'
        if not path.exists():
            self.skipTest('Set OMLX_SOURCE to v0.8.3 checkout for native TextArgs CPU test')
        tree = ast.parse(path.read_text())
        node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'TextArgs')
        namespace = {'dataclass':dataclass}
        tree = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0),node], type_ignores=[])
        exec(compile(ast.fix_missing_locations(tree), str(path), 'exec'), namespace)
        args_cls = namespace['TextArgs']
        for passes, visits in [(1,24),(2,36),(3,48),(5,72)]:
            args = args_cls.from_dict({'num_hidden_layers':24,'loop_num_passes':passes,
                'loop_config': {'core_start':6,'core_end':18,'num_passes':3,'is_varloop':True}})
            schedule = args.layer_schedule()
            self.assertEqual(len(schedule), visits)
            self.assertEqual(Counter(i for i,p in schedule)[8], passes)
            self.assertEqual(Counter(i for i,p in schedule)[0], 1)

    def test_all_passes_batches_resume_and_hook_failure(self):
        with tempfile.TemporaryDirectory() as tmp, stub_module.Stub() as stub:
            root = Path(tmp)
            subset = selection()
            subset['longmemeval'] = subset['longmemeval'][:3]
            subset['locomo'] = subset['locomo'][:3]
            selected = root / 'subset.json'
            selected.write_text(json.dumps(subset))
            hook_count = root / 'hooks'
            hook = 'echo restart >> ' + str(hook_count)
            for passes in (1,2,3,5):
                before = len(stub.calls)
                batch(passes, selected, root, 'stub-reader', stub.url, hook, 5,
                      {'longmemeval':stub.url, 'locomo':stub.url})
                run = root / f'varloop-p{passes}'
                for lab in ('longmemeval','locomo'):
                    self.assertTrue(read(run / lab / 'summary.json')['complete'])
                    self.assertEqual(read(run / lab / 'summary.json')['completed'], 15)
                    manifest = read(run / lab / 'manifest.json')
                    self.assertEqual(manifest['thinking_budget'], 0)
                    self.assertEqual(manifest['judge']['base'], stub.url)
                self.assertEqual(read(run / 'locomo/matched-summary.json')['item_ids'], subset['locomo'])
                self.assertTrue(read(run / 'locomo/matched-summary.json')['complete'])
                self.assertGreater(len(stub.calls), before)
                completed = len(stub.calls)
                batch(passes, selected, root, 'stub-reader', stub.url, hook, 5,
                      {'longmemeval':stub.url, 'locomo':stub.url})
                self.assertEqual(len(stub.calls), completed)
            self.assertEqual(len(hook_count.read_text().splitlines()), 24) # 5/run + 1/resume
            for call in stub.calls:
                if call['model'] == 'stub-reader':
                    self.assertEqual(call['thinking_budget'], 0)
                    self.assertFalse(call['chat_template_kwargs']['enable_thinking'])
                    self.assertEqual(call['temperature'], 0)
                else:
                    self.assertNotIn('thinking_budget', call)
            with self.assertRaises(subprocess.CalledProcessError):
                batch(1, selected, root / 'fail', 'stub-reader', stub.url, 'exit 7', 5,
                      {'longmemeval':stub.url, 'locomo':stub.url})
            state = read(root / 'fail/varloop-p1/longmemeval/summary.json')
            self.assertEqual(state['completed'], 5)
            subset['locomo'].reverse()
            selected.write_text(json.dumps(subset))
            with self.assertRaises(RuntimeError):
                batch(1, selected, root, 'stub-reader', stub.url, hook, 5)

    def test_owns_server_accepts_rewritten_process_title_only_with_listener(self):
        from types import SimpleNamespace as R
        root = Path('/lab/memory-loops')

        def runner(listening, command):
            def run(argv, **kw):
                if argv[0] == 'ps':
                    return R(stdout=command, returncode=0)
                return R(stdout='omlx-ser 1 u 5u IPv4 TCP 127.0.0.1:39851 (LISTEN)' if listening else '', returncode=0 if listening else 1)
            return run
        self.assertTrue(owns_server(7, root, runner(True, 'omlx-server')))
        self.assertFalse(owns_server(7, root, runner(False, 'omlx-server')))
        self.assertTrue(owns_server(7, root, runner(False, f'x {root}/omlx-data --port 39851')))

    def test_owned_server_lifecycle_with_stub(self):
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(('127.0.0.1', 39851))
            except OSError:
                self.skipTest('Port 39851 occupied; never disturb its owner')
        with tempfile.TemporaryDirectory() as tmp:
            lab = Path(tmp)
            root = lab / 'memory-loops'
            root.mkdir()
            src = lab / 'source'
            src.mkdir()
            (src / 'config.json').write_text(json.dumps({'model_type':'inkling2_loop',
                'text_config':{'loop_config':{'core_start':6,'core_end':18,'num_passes':3,'is_varloop':True}}}))
            binary = lab / 'omlx-venv/bin/omlx'
            binary.parent.mkdir(parents=True)
            binary.write_text("""#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import json, sys
from pathlib import Path
model = next(Path(sys.argv[sys.argv.index('--model-dir')+1]).iterdir()).name
class Handler(BaseHTTPRequestHandler):
    def reply(self, body):
        value = json.dumps(body).encode()
        self.send_response(200)
        self.send_header('Content-Length',str(len(value)))
        self.end_headers()
        self.wfile.write(value)
    def do_GET(self):
        self.reply({'data':[{'id':model}]})
    def do_POST(self):
        self.rfile.read(int(self.headers['Content-Length']))
        self.reply({'choices':[{'message':{'content':'OK'}}], 'usage':{}})
HTTPServer(('127.0.0.1',39851),Handler).serve_forever()
""")
            binary.chmod(0o755)
            start_code = 'from pathlib import Path; import remote; remote.start(Path(%r),Path(%r),Path(%r),Path(%r),2)' % (
                str(lab),str(root),str(lab / 'heavy.lock'),str(src))
            stop_code = 'from pathlib import Path; import remote; remote.stop(Path(%r),Path(%r))' % (str(root),str(lab / 'heavy.lock'))
            try:
                result = subprocess.run([sys.executable,'-c',start_code],cwd=HERE,check=True,
                                        capture_output=True,text=True,timeout=20)
                self.assertEqual(json.loads(result.stdout)['passes'],2)
                self.assertTrue((lab / 'heavy.lock/memory-loops-owner').exists())
                self.assertTrue((root / 'warmup-p2.json').exists())
            finally:
                subprocess.run([sys.executable,'-c',stop_code],cwd=HERE,check=True,timeout=70)
            self.assertFalse((lab / 'heavy.lock').exists())
            self.assertFalse((root / 'server.json').exists())
            binary.write_text('#!/usr/bin/env python3\nraise SystemExit(7)\n')
            failure = subprocess.run([sys.executable,'-c',start_code],cwd=HERE,
                                     capture_output=True,text=True,timeout=20)
            self.assertNotEqual(failure.returncode,0)
            self.assertFalse((lab / 'heavy.lock').exists())
            self.assertFalse((root / 'server.json').exists())

    def test_stop_refuses_unrelated_pid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lock = root / 'heavy.lock'
            lock.mkdir()
            (lock / 'memory-loops-owner').write_text(str(root))
            (root / 'server.json').write_text(json.dumps({'pid':os.getpid()}))
            with self.assertRaises(RuntimeError):
                stop(root, lock)
            self.assertTrue(lock.exists())
            self.assertTrue((root / 'server.json').exists())


if __name__ == '__main__':
    unittest.main()
