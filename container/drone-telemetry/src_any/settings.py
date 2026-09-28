"""Container settings: built-in defaults < environment variables < CLI arguments."""

import argparse
import os
import socket

DEFAULTS = {
    "airsim_host": "127.0.0.1",
    "airsim_port": 41451,
    "carla_port": 2000,
    "vehicle_name": "SimpleFlight",
    "poll_interval_s": 1.0,
    "backend_url": "http://127.0.0.1:8080/telemetry",
    "drone_id": "drone-" + socket.gethostname(),
}

ENV_NAMES = {
    "airsim_host": "AIRSIM_HOST",
    "airsim_port": "AIRSIM_PORT",
    "carla_port": "CARLA_PORT",
    "vehicle_name": "VEHICLE_NAME",
    "poll_interval_s": "POLL_INTERVAL_S",
    "backend_url": "BACKEND_URL",
    "drone_id": "DRONE_ID",
}


def _env_default(key):
    value = os.environ.get(ENV_NAMES[key])
    if value is None:
        return DEFAULTS[key]
    return type(DEFAULTS[key])(value)


def load(argv=None):
    parser = argparse.ArgumentParser(
        description="AOS-Drones-PoC Container: read drone coordinates from CARLA-Air "
                    "(AirSim RPC), print them and forward them to the Container backend.")
    parser.add_argument("--airsim-host", default=_env_default("airsim_host"),
                        help="CARLA-Air host running AirSim RPC (env AIRSIM_HOST)")
    parser.add_argument("--airsim-port", type=int, default=_env_default("airsim_port"),
                        help="AirSim RPC port (env AIRSIM_PORT, default 41451)")
    parser.add_argument("--carla-port", type=int, default=_env_default("carla_port"),
                        help="CARLA RPC port, reachability check only (env CARLA_PORT, default 2000)")
    parser.add_argument("--vehicle-name", default=_env_default("vehicle_name"),
                        help="AirSim vehicle name (env VEHICLE_NAME, default SimpleFlight)")
    parser.add_argument("--poll-interval", dest="poll_interval_s", type=float,
                        default=_env_default("poll_interval_s"),
                        help="seconds between polls (env POLL_INTERVAL_S)")
    parser.add_argument("--backend-url", default=_env_default("backend_url"),
                        help="Container backend telemetry URL; empty disables forwarding (env BACKEND_URL)")
    parser.add_argument("--drone-id", default=_env_default("drone_id"),
                        help="drone identifier sent to the backend (env DRONE_ID)")
    parser.add_argument("--max-iterations", type=int, default=0,
                        help="stop after N successful polls (0 = run forever; used by tests)")
    return parser.parse_args(argv)
