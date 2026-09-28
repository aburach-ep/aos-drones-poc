"""Interface to drone: read-only AirSim msgpack-RPC client for CARLA-Air.

CARLA-Air exposes AirSim's RPC server (default TCP 41451). The protocol is
msgpack-RPC:

    request  = [0, msgid, method, params]
    response = [1, msgid, error, result]

Only read-only calls are used (``ping``, ``getMultirotorState``). The client
never calls ``enableApiControl``, so it does not take control of the drone.
"""

import socket
import threading
from dataclasses import dataclass, asdict

import msgpack_lite

LANDED_STATES = {0: "Landed", 1: "Flying"}


class AirSimError(Exception):
    """RPC-level error returned by the AirSim server or a broken connection."""


@dataclass
class DroneState:
    vehicle: str
    timestamp_ns: int
    x: float            # NED metres, origin = PlayerStart
    y: float
    z: float            # negative = above origin
    latitude: float
    longitude: float
    altitude: float     # metres
    landed_state: str

    def to_telemetry(self, drone_id):
        """Build the telemetry JSON contract shared with the Container backend."""
        return {
            "drone_id": drone_id,
            "vehicle": self.vehicle,
            "timestamp": self.timestamp_ns,
            "position_ned": {"x": self.x, "y": self.y, "z": self.z},
            "gps": {"lat": self.latitude, "lon": self.longitude, "alt": self.altitude},
            "landed_state": self.landed_state,
        }

    def as_dict(self):
        return asdict(self)

    def console_line(self):
        return (
            "[drone %s] t=%d NED x=%.2f y=%.2f z=%.2f m | "
            "GPS lat=%.6f lon=%.6f alt=%.1f m | landed=%s"
            % (self.vehicle, self.timestamp_ns, self.x, self.y, self.z,
               self.latitude, self.longitude, self.altitude, self.landed_state)
        )


class AirSimClient(object):
    """Blocking, thread-safe msgpack-RPC client (one request in flight)."""

    def __init__(self, host="127.0.0.1", port=41451, timeout=5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock = None
        self._unpacker = None
        self._msgid = 0
        self._lock = threading.Lock()

    # -- connection -------------------------------------------------------

    def connect(self):
        self.close()
        self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._unpacker = msgpack_lite.Unpacker()

    def close(self):
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
        self._sock = None

    @property
    def connected(self):
        return self._sock is not None

    # -- RPC --------------------------------------------------------------

    def call(self, method, *params):
        with self._lock:
            if self._sock is None:
                self.connect()
            self._msgid = (self._msgid + 1) & 0xFFFFFFFF
            msgid = self._msgid
            try:
                self._sock.sendall(msgpack_lite.packb([0, msgid, method, list(params)]))
                while True:
                    for message in self._unpacker:
                        if (isinstance(message, list) and len(message) == 4
                                and message[0] == 1 and message[1] == msgid):
                            error, result = message[2], message[3]
                            if error is not None:
                                raise AirSimError("%s failed: %r" % (method, error))
                            return result
                    chunk = self._sock.recv(65536)
                    if not chunk:
                        raise AirSimError("connection closed by AirSim server")
                    self._unpacker.feed(chunk)
            except (OSError, AirSimError):
                self.close()
                raise

    def ping(self):
        return bool(self.call("ping"))

    def get_multirotor_state(self, vehicle_name=""):
        return self.call("getMultirotorState", vehicle_name)

    def get_drone_state(self, vehicle_name):
        return parse_multirotor_state(self.get_multirotor_state(vehicle_name), vehicle_name)


def _num(d, key, default=0.0):
    value = d.get(key, default) if isinstance(d, dict) else default
    return float(value) if value is not None else default


def parse_multirotor_state(raw, vehicle_name):
    """Convert AirSim's MultirotorState map into a DroneState."""
    if not isinstance(raw, dict):
        raise AirSimError("unexpected getMultirotorState result: %r" % (raw,))
    kin = raw.get("kinematics_estimated") or {}
    pos = kin.get("position") or {}
    gps = raw.get("gps_location") or {}
    landed = raw.get("landed_state", -1)
    return DroneState(
        vehicle=vehicle_name or "default",
        timestamp_ns=int(raw.get("timestamp") or 0),
        x=_num(pos, "x_val"),
        y=_num(pos, "y_val"),
        z=_num(pos, "z_val"),
        latitude=_num(gps, "latitude"),
        longitude=_num(gps, "longitude"),
        altitude=_num(gps, "altitude"),
        landed_state=LANDED_STATES.get(landed, str(landed)),
    )


def tcp_reachable(host, port, timeout=2.0):
    """True if a TCP connection to host:port can be opened (used for CARLA :2000)."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
