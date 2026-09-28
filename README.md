# AOS-Drones-PoC — MVP

This folder holds the MVP implementation of the **AOS-Drones-PoC diagram** described in `C:\DOCs\PreSales\aos-2026-Sept\AOS-Drones-PoC-Concept.md`. It contains two independent Python projects, both using only the standard library:

| Project | Diagram element | Runs on | Deployed by |
|---|---|---|---|
| [container/](container/README.md) | **Container** (includes the *Interface to drone* AirSim client) | AosVM (drone Unit), or natively on Windows for local tests | ServiceProvider → `aos-signer` → AosCloud → AosCore |
| [container_backend/](container_backend/README.md) | **Container backend** | Windows host (later: SP cloud) | Started by hand (`scripts/run-backend.ps1`) |

The two projects share only the telemetry JSON contract, which is documented in both READMEs. The implementation plan, including the answers to the ServiceProvider and backend questions, is in [AOS-Drones-PoC-impl-Plan.md](AOS-Drones-PoC-impl-Plan.md).

## Quick start (local, no AOS)

```powershell
# 0) CARLA-Air running (C:\workspace\carla-air\CarlaAir-v0.1.7\StartCarlaAir.bat)
# 1) Terminal 1 — backend
.\container_backend\scripts\run-backend.ps1
# 2) Terminal 2 — container: prints drone coordinates every second
.\container\scripts\run-local.ps1
# 3) Check what the backend received
curl.exe http://127.0.0.1:8080/telemetry/latest
```

## Tests

```powershell
cd container;         python -m unittest discover tests -v; cd ..
cd container_backend; python -m unittest discover tests -v; cd ..
```
