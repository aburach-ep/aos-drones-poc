"""AOS-Drones-PoC Container backend (Service Provider side, PoC scope).

Receives drone telemetry from the Container (C5 link), prints it and keeps
the most recent records in memory.

Endpoints:
    POST /telemetry         telemetry JSON (see README.md, "Telemetry contract")
    GET  /telemetry/latest  latest record per drone
    GET  /telemetry         last N records (newest last)
    GET  /health            liveness
"""

import argparse
import json
import os
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REQUIRED_KEYS = {
    "drone_id": str,
    "vehicle": str,
    "timestamp": int,
    "position_ned": dict,
    "gps": dict,
    "landed_state": str,
}
NESTED_KEYS = {"position_ned": ("x", "y", "z"), "gps": ("lat", "lon", "alt")}


def validate(record):
    """Return an error message, or None if ``record`` matches the telemetry contract."""
    if not isinstance(record, dict):
        return "body must be a JSON object"
    for key, kind in REQUIRED_KEYS.items():
        if key not in record:
            return "missing field '%s'" % key
        if not isinstance(record[key], kind) or isinstance(record[key], bool):
            return "field '%s' must be %s" % (key, kind.__name__)
    for key, fields in NESTED_KEYS.items():
        for field in fields:
            value = record[key].get(field)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return "field '%s.%s' must be a number" % (key, field)
    return None


class TelemetryStore(object):
    def __init__(self, history=1000):
        self._lock = threading.Lock()
        self._history = deque(maxlen=history)
        self._latest = {}

    def add(self, record):
        with self._lock:
            self._history.append(record)
            self._latest[record["drone_id"]] = record

    def latest(self):
        with self._lock:
            return dict(self._latest)

    def history(self):
        with self._lock:
            return list(self._history)


class Handler(BaseHTTPRequestHandler):
    server_version = "aos-drones-poc-backend/0.1"

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        if path == "/health":
            self._json(200, {"status": "ok", "uptime_s": round(time.time() - self.server.started, 1)})
        elif path == "/telemetry/latest":
            self._json(200, self.server.store.latest())
        elif path == "/telemetry":
            self._json(200, self.server.store.history())
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path.split("?", 1)[0].rstrip("/") != "/telemetry":
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            record = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._json(400, {"error": "invalid JSON"})
            return
        error = validate(record)
        if error:
            self._json(400, {"error": error})
            return
        record["received_at"] = time.time()
        self.server.store.add(record)
        p, g = record["position_ned"], record["gps"]
        print("[backend] %s from %s: NED x=%.2f y=%.2f z=%.2f m | GPS lat=%.6f lon=%.6f alt=%.1f m | %s"
              % (record["drone_id"], self.client_address[0], p["x"], p["y"], p["z"],
                 g["lat"], g["lon"], g["alt"], record["landed_state"]), flush=True)
        self._json(202, {"status": "accepted"})

    def _json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass  # telemetry is printed explicitly; skip per-request access log


class BackendServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, host, port, history=1000):
        ThreadingHTTPServer.__init__(self, (host, port), Handler)
        self.store = TelemetryStore(history)
        self.started = time.time()


def main(argv=None):
    ap = argparse.ArgumentParser(description="AOS-Drones-PoC Container backend")
    ap.add_argument("--host", default=os.environ.get("BACKEND_HOST", "0.0.0.0"),
                    help="bind address (env BACKEND_HOST, default 0.0.0.0 so the AosVM can reach it)")
    ap.add_argument("--port", type=int, default=int(os.environ.get("BACKEND_PORT", "8080")),
                    help="listen port (env BACKEND_PORT, default 8080)")
    ap.add_argument("--history", type=int, default=1000, help="records kept in memory")
    args = ap.parse_args(argv)

    server = BackendServer(args.host, args.port, args.history)
    print("[backend] listening on http://%s:%d  (POST /telemetry, GET /telemetry/latest, GET /health)"
          % (args.host, args.port), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[backend] stopping", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
