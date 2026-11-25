"""Offline canned OpenAI-compatible server. Never contacts an upstream endpoint."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading


class Stub:
    def __init__(self):
        self.calls = []
        self.fail_at = None
        self.wrong_judge = False
        self.length_once = False
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path != '/v1/chat/completions':
                    self.send_error(404)
                    return
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                owner.calls.append(body)
                if owner.fail_at == len(owner.calls):
                    self.send_error(503, 'canned interruption')
                    return
                model = body['model']
                content = ('yes' if model == 'default_model' else
                           '{"reasoning":"canned judge","label":"CORRECT"}' if model == 'qwen2.5-14b-instruct' else
                           'A' if 'Return only the letter' in body['messages'][-1]['content'] else 'Final answer: 2')
                if owner.wrong_judge and model == 'default_model':
                    content = 'no'
                elif owner.wrong_judge and model == 'qwen2.5-14b-instruct':
                    content = '{"reasoning":"canned negative judge","label":"WRONG"}'
                finish = 'stop'
                if owner.length_once and model == 'stub-reader':
                    finish = 'length'
                    owner.length_once = False
                payload = json.dumps({'id': f'stub-{len(owner.calls)}', 'object': 'chat.completion',
                                      'model': model, 'choices': [{'index': 0, 'finish_reason': finish,
                                      'message': {'role': 'assistant', 'content': content}}],
                                      'usage': {'prompt_tokens': 10, 'completion_tokens': 2, 'total_tokens': 12}}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.server.server_port}/v1'
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


if __name__ == '__main__':
    with Stub() as stub:
        print(stub.url, flush=True)
        threading.Event().wait()
