# AOS-Drones-PoC — Container

The **Container** is the Service Provider's drone application. In the AOS-Drones-PoC diagram it runs inside the drone's VM (AosVM) as an **Aos service**, started and isolated by **AosCore** after deployment through **AosCloud**.

For this MVP it:

1. Reads the simulated drone's coordinates from local **CARLA-Air 0.1.7** through the **AirSim RPC API (TCP 41451)**. This is the *Interface to drone* part.
2. **Prints** them to the console. Locally you see them in the terminal; on the unit they end up in the AosCore service log in AosCloud.
3. Sends them as JSON telemetry to the **Container backend** (link C5).

It also checks that **CARLA RPC (TCP 2000)** is reachable when it starts. The CARLA Python client is a Windows-only wheel, so it cannot run in the Linux AosVM, and all data therefore comes from AirSim.

## Why only the standard library

Aos Python services are **not Docker images**. `aos-signer` packages the source folder, and AosCore runs it with the unit's own `/usr/bin/python3`. The AOS hello-world does the same: `cmd: /usr/bin/python3 -u webhook_example.py`. The PyPI `airsim` package needs `msgpack-rpc-python`/tornado and is not available there. The Container therefore contains:

- a small **msgpack codec** (`msgpack_lite.py`);
- a **read-only AirSim msgpack-RPC client** (`drone_interface.py`).

The client only calls `ping` and `getMultirotorState`. It never calls `enableApiControl`, so it does not take control of the drone away from the keyboard or other scripts.

## Layout

```
container/
  config.yaml                      # aos-signer bundle config (schemaVersion 2, like aosedge/hello-world)
  drone-telemetry/                 # service source folder (items[].sourceFolder)
    src_any/                       # image for architecture "any" -> copied to "/" in the service
      main.py                      # entry point: poll -> print -> POST, reconnect with backoff
      drone_interface.py           # Interface to drone: AirSimClient, DroneState, tcp_reachable()
      msgpack_lite.py              # minimal MessagePack pack/unpack
      backend_client.py            # POST telemetry JSON (urllib), never crashes the loop
      settings.py                  # defaults < env vars < CLI args
  scripts/
    run-local.ps1                  # run natively on Windows against local CARLA-Air
    sign-and-upload.ps1            # SP: aos-signer sign + upload
    check-network.ps1              # listen addresses of 41451/2000/8080, optional firewall rules
  tests/                           # offline tests (fake AirSim RPC server, fake backend)
```

## Settings

| CLI | Env var | Default | Meaning |
|---|---|---|---|
| `--airsim-host` | `AIRSIM_HOST` | `127.0.0.1` | Host running CARLA-Air |
| `--airsim-port` | `AIRSIM_PORT` | `41451` | AirSim RPC port |
| `--carla-port` | `CARLA_PORT` | `2000` | CARLA RPC port (reachability check only) |
| `--vehicle-name` | `VEHICLE_NAME` | `SimpleFlight` | AirSim vehicle; see `CarlaAir-v0.1.7\AirSimConfig\settings.json` |
| `--poll-interval` | `POLL_INTERVAL_S` | `1.0` | Seconds between polls |
| `--backend-url` | `BACKEND_URL` | `http://127.0.0.1:8080/telemetry` | Container backend; an empty value turns forwarding off |
| `--drone-id` | `DRONE_ID` | `drone-<hostname>` | Identifier sent to the backend |
| `--max-iterations` | — | `0` (run forever) | Stop after N polls (used by tests) |

## Run locally on Windows (no AOS)

Requirements: Python 3.8+ (only the standard library), and CARLA-Air started with `CarlaAir-v0.1.7\StartCarlaAir.bat`.

```powershell
# 1) Container backend (separate project), in a first terminal
..\container_backend\scripts\run-backend.ps1
# 2) Container, in a second terminal
.\scripts\run-local.ps1
```

Console output, one line per poll:

```
[container] AOS-Drones-PoC Container starting: drone_id=drone-local-01 vehicle=SimpleFlight
[container] AirSim 127.0.0.1:41451, backend http://127.0.0.1:8080/telemetry
[container] CARLA RPC 127.0.0.1:2000 reachable: yes
[container] connected to AirSim at 127.0.0.1:41451
[drone SimpleFlight] t=1790419432397845248 NED x=-0.05 y=0.05 z=29.24 m | GPS lat=47.639921 lon=-122.137713 alt=120.4 m | landed=Landed
[backend] delivering telemetry to http://127.0.0.1:8080/telemetry
```

To see the coordinates change, fly the drone, for example with `CarlaAir-v0.1.7\examples\fly_drone_keyboard.py` in the `carlaAir` conda env.

**How to read the coordinates:**

- **NED** is AirSim's local frame. It is in metres, its origin is PlayerStart, and **z is positive downwards**. A landed drone can therefore show z > 0, and a climbing drone shows z decreasing.
- **GPS** is AirSim's geodetic position of the drone: latitude, longitude and altitude in metres.

## Deploy to the drone Unit through AOS (Service Provider flow)

The ServiceProvider is not a component you run. It is your **SP role/account in AosCloud** plus the `aos-signer` tool.

1. **One-time setup:** create the SP certificate from the SP token in your AosCloud sign-up email:
   ```powershell
   . C:\workspace\carla-air\aos\aos-env.ps1
   aos-keys new-user -d aoscloud.io -t <SP token> --sp      # -> %USERPROFILE%\.aos\security\aos-user-sp.p12
   ```
2. **Set the host IP** in the `cmd` line of `config.yaml` (see *AosVM networking* below). The default is `10.0.2.2`.
3. **Sign and upload.** The service is created in AosCloud on the first upload:
   ```powershell
   .\scripts\sign-and-upload.ps1
   ```
4. **Install on the Unit:** in the **OEM** portal (https://oem.aoscloud.io) go to **Subjects → +**, add the service `aos-drones-poc-container`, then assign the drone Unit (AosVM). Subjects are an OEM permission; the SP account cannot create them. For the short step-by-step guide, see [PUBLISH.md](PUBLISH.md).
5. **Check:** the Unit's service status shows *active*. Request the service log in AosCloud: it contains the `[drone SimpleFlight] ...` lines. The backend console on the host shows the telemetry arriving.

**Updating:** bump `version` in `config.yaml`, then run `sign-and-upload.ps1` again. AosCloud rolls out the new version and can roll it back.

## AosVM networking

CARLA-Air and the backend run on the **Windows host**. The Container runs **inside the AosVM**, so it has to reach the host over the VirtualBox network.

| Check | How |
|---|---|
| Host IP as seen from the VM | `ssh -p 8143 root@localhost` (node0), then `ip route`. With VirtualBox NAT the host is normally `10.0.2.2`. |
| CARLA-Air listens on all interfaces | `.\scripts\check-network.ps1`. It was verified that 41451 and 2000 listen on `0.0.0.0`. |
| Windows firewall allows 41451, 2000 and 8080 inbound | `.\scripts\check-network.ps1 -AddFirewallRules` (as Administrator) |
| Service outbound network | Outbound connections work by default: the hello-world reaches webhook.site. If the unit restricts networking, allow outbound TCP to the host. |

## Telemetry contract (Container → Container backend)

`POST <backend-url>` with `Content-Type: application/json`:

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

`timestamp` is AirSim's simulation timestamp in nanoseconds. `landed_state` is `Landed` or `Flying`. The same contract is documented in `../container_backend/README.md`.

## Tests

```powershell
cd container
python -m unittest discover tests -v
```

The tests cover:

- the msgpack codec;
- the AirSim client against a fake AirSim RPC server;
- an end-to-end run: fake AirSim → `main.py` → fake backend.

None of them need CARLA-Air. `python tests\fake_airsim_server.py` also starts a standalone fake drone on 41451, for demos without the simulator. Stop CARLA-Air first if you use port 41451.
