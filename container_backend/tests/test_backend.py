import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend import BackendServer  # noqa: E402

SAMPLE = {
    "drone_id": "drone-test",
    "vehicle": "SimpleFlight",
    "timestamp": 1790000000000000000,
    "position_ned": {"x": 1.5, "y": -2.0, "z": -10.0},
    "gps": {"lat": 47.641468, "lon": -122.140165, "alt": 132.0},
    "landed_state": "Flying",
}


class BackendTest(unittest.TestCase):
    def setUp(self):
        self.server = BackendServer("127.0.0.1", 0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def request(self, method, path, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read())

    def test_health(self):
        status, body = self.request("GET", "/health")
        self.assertEqual((status, body["status"]), (200, "ok"))

    def test_post_and_latest(self):
        status, _ = self.request("POST", "/telemetry", SAMPLE)
        self.assertEqual(status, 202)
        status, latest = self.request("GET", "/telemetry/latest")
        self.assertEqual(status, 200)
        self.assertEqual(latest["drone-test"]["position_ned"], SAMPLE["position_ned"])
        _, history = self.request("GET", "/telemetry")
        self.assertEqual(len(history), 1)

    def test_rejects_invalid(self):
        bad = dict(SAMPLE, gps={"lat": "x", "lon": 0, "alt": 0})
        status, body = self.request("POST", "/telemetry", bad)
        self.assertEqual(status, 400)
        self.assertIn("gps.lat", body["error"])
        status, _ = self.request("POST", "/telemetry", {"drone_id": "x"})
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
