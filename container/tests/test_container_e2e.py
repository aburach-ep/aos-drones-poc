"""End-to-end without CARLA-Air: fake AirSim -> Container (subprocess) -> fake backend."""

import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "drone-telemetry", "src_any")
sys.path.insert(0, HERE)
sys.path.insert(0, SRC)

from fake_airsim_server import FakeAirSimServer  # noqa: E402
from fake_backend import FakeBackend  # noqa: E402
from drone_interface import AirSimClient  # noqa: E402

TELEMETRY_KEYS = {"drone_id", "vehicle", "timestamp", "position_ned", "gps", "landed_state"}


class AirSimClientTest(unittest.TestCase):
    def setUp(self):
        self.airsim = FakeAirSimServer().start()

    def tearDown(self):
        self.airsim.shutdown()
        self.airsim.server_close()

    def test_ping_and_state(self):
        client = AirSimClient("127.0.0.1", self.airsim.port)
        self.assertTrue(client.ping())
        state = client.get_drone_state("SimpleFlight")
        self.assertEqual(state.vehicle, "SimpleFlight")
        self.assertNotEqual(state.latitude, 0.0)
        self.assertIn(("getMultirotorState", ["SimpleFlight"]), self.airsim.calls)
        client.close()


class ContainerE2ETest(unittest.TestCase):
    def setUp(self):
        self.airsim = FakeAirSimServer().start()
        self.backend = FakeBackend().start()

    def tearDown(self):
        for server in (self.airsim, self.backend):
            server.shutdown()
            server.server_close()

    def test_container_prints_and_forwards(self):
        cmd = [sys.executable, "-u", "main.py",
               "--airsim-port", str(self.airsim.port),
               "--carla-port", "1",
               "--backend-url", self.backend.url,
               "--poll-interval", "0.05",
               "--drone-id", "test-drone",
               "--max-iterations", "3"]
        proc = subprocess.run(cmd, cwd=SRC, capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        lines = [l for l in proc.stdout.splitlines() if l.startswith("[drone SimpleFlight]")]
        self.assertEqual(len(lines), 3, proc.stdout)
        self.assertIn("GPS lat=", lines[0])

        self.assertEqual(len(self.backend.received), 3)
        record = self.backend.received[0]
        self.assertEqual(set(record), TELEMETRY_KEYS)
        self.assertEqual(record["drone_id"], "test-drone")
        self.assertEqual(set(record["position_ned"]), {"x", "y", "z"})
        self.assertEqual(set(record["gps"]), {"lat", "lon", "alt"})


if __name__ == "__main__":
    unittest.main()
