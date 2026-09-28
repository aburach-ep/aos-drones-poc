# AOS-Drones-PoC — Container backend

The **Container backend** is the Service Provider's own server side for the drone application: the "Container backend" box in the AOS-Drones-PoC diagram. It receives telemetry from the Container (link C5, Container → Container backend).

AosCloud does **not** offer a backend for Service Providers. It handles orchestration and monitoring only. The SP always hosts its own backend. In this PoC it is a small, standard-library-only HTTP server on the **Windows host**, next to CARLA-Air. Later it can move to the SP's cloud without any change to the Container, apart from the URL.

## What it does

- Accepts telemetry records, validates them against the telemetry contract and **prints** each one.
- Keeps the latest record per drone and the last *N* records (default 1000) **in memory**. Nothing is persisted in the PoC.
- Serves the data back over HTTP for checks and demos.

## Endpoints

| Method | Path | Response |
|---|---|---|
| `POST` | `/telemetry` | `202 {"status":"accepted"}`, or `400 {"error": "..."}` if the body breaks the contract |
| `GET` | `/telemetry/latest` | `{"<drone_id>": <latest record>, ...}` |
| `GET` | `/telemetry` | List of the last N records, newest last |
| `GET` | `/health` | `{"status":"ok","uptime_s":...}` |

Each stored record gets an extra field, `received_at`: the Unix time at which the backend received it.

## Telemetry contract (Container → Container backend)

```json
{
  "drone_id": "drone-aosvm-01",
  "vehicle": "SimpleFlight",
  "timestamp": 1790419432397845248,
  "position_ned": {"x": -0.05, "y": 0.05, "z": 29.24},
  "gps": {"lat": 47.639921, "lon": -122.137713, "alt": 120.4},
  "landed_state": "Landed"
}
```

| Field | Type | Meaning |
|---|---|---|
| `drone_id` | string | Drone / unit identifier set in the Container |
| `vehicle` | string | AirSim vehicle name |
| `timestamp` | integer | AirSim simulation time, nanoseconds |
| `position_ned` | object `{x,y,z}` numbers | AirSim local NED position, metres; origin PlayerStart, z positive downwards |
| `gps` | object `{lat,lon,alt}` numbers | Geodetic position; alt in metres |
| `landed_state` | string | `Landed` / `Flying` |

The same contract is documented in `../container/README.md`.

## Run

Requirements: Python 3.8+ (only the standard library).

```powershell
.\scripts\run-backend.ps1                   # listens on 0.0.0.0:8080
.\scripts\run-backend.ps1 -Port 9090        # other port
python backend.py --host 127.0.0.1          # local-only
```

| CLI | Env var | Default |
|---|---|---|
| `--host` | `BACKEND_HOST` | `0.0.0.0`, so the AosVM can reach it |
| `--port` | `BACKEND_PORT` | `8080` |
| `--history` | — | `1000` |

Console output:

```
[backend] listening on http://0.0.0.0:8080  (POST /telemetry, GET /telemetry/latest, GET /health)
[backend] drone-local-01 from 127.0.0.1: NED x=-0.05 y=0.05 z=29.24 m | GPS lat=47.639921 lon=-122.137713 alt=120.4 m | Landed
```

When the Container runs in the AosVM, the source address is the VM's NAT address rather than `127.0.0.1`.

## Reachability from the AosVM

- The Container in the AosVM calls `http://<HOST_IP>:8080/telemetry`. With VirtualBox NAT, `<HOST_IP>` is normally `10.0.2.2`; see `../container/README.md`, *AosVM networking*.
- Allow inbound TCP 8080 in the Windows firewall (as Administrator):
  ```powershell
  New-NetFirewallRule -DisplayName "AOS-Drones-PoC TCP 8080" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow
  ```
  Or run `..\container\scripts\check-network.ps1 -AddFirewallRules`.

## Try it by hand

```powershell
curl.exe http://127.0.0.1:8080/health
curl.exe -X POST http://127.0.0.1:8080/telemetry -H "Content-Type: application/json" `
  -d '{\"drone_id\":\"manual\",\"vehicle\":\"SimpleFlight\",\"timestamp\":1,\"position_ned\":{\"x\":1,\"y\":2,\"z\":-3},\"gps\":{\"lat\":47.6,\"lon\":-122.1,\"alt\":120},\"landed_state\":\"Flying\"}'
curl.exe http://127.0.0.1:8080/telemetry/latest
```

## Tests

```powershell
cd container_backend
python -m unittest discover tests -v
```

## Next steps (out of PoC scope)

- Persistent storage (SQLite or time-series DB) and a map dashboard
- A mission endpoint (backend → Container), for the "Fly a mission" flow in the concept
- HTTPS and authentication, and hosting in the SP cloud
