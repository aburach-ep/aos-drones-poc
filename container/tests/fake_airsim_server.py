"""Stdlib fake of CARLA-Air's AirSim msgpack-RPC server, for offline tests.

Run standalone to try the Container without CARLA-Air:
    python tests/fake_airsim_server.py --port 41451
The fake drone climbs and circles slowly.
"""

import argparse
import math
import os
import socketserver
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "drone-telemetry", "src_any"))
import msgpack_lite  # noqa: E402

HOME_LAT, HOME_LON, HOME_ALT = 47.641468, -122.140165, 122.0


def fake_state(t):
    x, y, z = 20.0 * math.cos(t / 10.0), 20.0 * math.sin(t / 10.0), -min(30.0, 2.0 * t)
    return {
        "collision": {"has_collided": False},
        "kinematics_estimated": {
            "position": {"x_val": x, "y_val": y, "z_val": z},
            "orientation": {"w_val": 1.0, "x_val": 0.0, "y_val": 0.0, "z_val": 0.0},
        },
        "gps_location": {
            "latitude": HOME_LAT + x / 111320.0,
            "longitude": HOME_LON + y / (111320.0 * math.cos(math.radians(HOME_LAT))),
            "altitude": HOME_ALT - z,
        },
        "timestamp": int(time.time() * 1e9),
        "landed_state": 1 if z < -0.5 else 0,
        "ready": True,
    }


class _Handler(socketserver.BaseRequestHandler):
    def handle(self):
        unpacker = msgpack_lite.Unpacker()
        while True:
            data = self.request.recv(65536)
            if not data:
                return
            unpacker.feed(data)
            for msg in unpacker:
                _type, msgid, method, params = msg
                self.server.calls.append((method, params))
                if method == "ping":
                    reply = [1, msgid, None, True]
                elif method == "getMultirotorState":
                    reply = [1, msgid, None, fake_state(time.time() - self.server.t0)]
                else:
                    reply = [1, msgid, "unknown method " + method, None]
                self.request.sendall(msgpack_lite.packb(reply))


class FakeAirSimServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, host="127.0.0.1", port=0):
        socketserver.ThreadingTCPServer.__init__(self, (host, port), _Handler)
        self.calls = []
        self.t0 = time.time()

    @property
    def port(self):
        return self.server_address[1]

    def start(self):
        threading.Thread(target=self.serve_forever, daemon=True).start()
        return self


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=41451)
    args = ap.parse_args()
    server = FakeAirSimServer(args.host, args.port)
    print("Fake AirSim RPC listening on %s:%d" % (args.host, server.port), flush=True)
    server.serve_forever()
