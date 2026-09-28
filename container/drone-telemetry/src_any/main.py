"""AOS-Drones-PoC Container entry point.

Polls the simulated drone in CARLA-Air through AirSim RPC, prints its
coordinates to the console (captured by AosCore logs) and forwards them to
the Container backend.
"""

import signal
import sys
import time

import settings
from backend_client import BackendClient
from drone_interface import AirSimClient, AirSimError, tcp_reachable

MAX_BACKOFF_S = 10.0


def log(message):
    print(message, flush=True)


def run(cfg):
    log("[container] AOS-Drones-PoC Container starting: drone_id=%s vehicle=%s"
        % (cfg.drone_id, cfg.vehicle_name))
    log("[container] AirSim %s:%d, backend %s"
        % (cfg.airsim_host, cfg.airsim_port, cfg.backend_url or "<disabled>"))

    carla_ok = tcp_reachable(cfg.airsim_host, cfg.carla_port)
    log("[container] CARLA RPC %s:%d reachable: %s"
        % (cfg.airsim_host, cfg.carla_port, "yes" if carla_ok else "no"))

    airsim = AirSimClient(cfg.airsim_host, cfg.airsim_port)
    backend = BackendClient(cfg.backend_url)
    stopping = {"flag": False}

    def _stop(signum, _frame):
        log("[container] signal %d received, stopping" % signum)
        stopping["flag"] = True

    signal.signal(signal.SIGINT, _stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _stop)

    polls = 0
    backoff = 1.0
    while not stopping["flag"]:
        try:
            if not airsim.connected:
                airsim.connect()
                airsim.ping()
                log("[container] connected to AirSim at %s:%d" % (cfg.airsim_host, cfg.airsim_port))
                backoff = 1.0
            state = airsim.get_drone_state(cfg.vehicle_name)
        except (OSError, AirSimError) as exc:
            log("[container] AirSim unavailable (%s); retry in %.0f s" % (exc, backoff))
            _sleep(backoff, stopping)
            backoff = min(backoff * 2, MAX_BACKOFF_S)
            continue

        log(state.console_line())
        backend.send(state.to_telemetry(cfg.drone_id))

        polls += 1
        if cfg.max_iterations and polls >= cfg.max_iterations:
            break
        _sleep(cfg.poll_interval_s, stopping)

    airsim.close()
    log("[container] stopped after %d polls" % polls)
    return 0


def _sleep(seconds, stopping):
    deadline = time.monotonic() + seconds
    while not stopping["flag"] and time.monotonic() < deadline:
        time.sleep(min(0.2, max(0.0, deadline - time.monotonic())))


if __name__ == "__main__":
    sys.exit(run(settings.load()))
