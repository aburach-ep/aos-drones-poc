"""Minimal HTTP sink that records POSTed telemetry (no dependency on container_backend)."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.server.received.append(json.loads(self.rfile.read(length)))
        self.send_response(202)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *_args):
        pass


class FakeBackend(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self):
        ThreadingHTTPServer.__init__(self, ("127.0.0.1", 0), _Handler)
        self.received = []

    @property
    def url(self):
        return "http://127.0.0.1:%d/telemetry" % self.server_address[1]

    def start(self):
        threading.Thread(target=self.serve_forever, daemon=True).start()
        return self
