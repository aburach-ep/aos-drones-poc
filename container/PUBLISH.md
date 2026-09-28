# Publish the Container to AosCloud

Publishing needs **two AosCloud accounts**, and each one can only do its own part:

| Step | Account / portal | Certificate | Why this account |
|---|---|---|---|
| Upload the Container (creates the **Service**) | **Service Provider**, https://sp.aoscloud.io/sp | `aos-user-sp.p12` | Only the SP has `services_create` / `services_versions_create` |
| Create a **Subject**, add the Service, assign the Unit | **OEM**, https://oem.aoscloud.io | `aos-user-oem.p12` (browser login) | Only the OEM has `subjects_create`, `subjects_services_create`, `subjects_units_create` |

The OEM account **cannot** publish the Container itself: it has no `services_create` permission. The Container backend is **not** published at all; it runs on the Windows host.

Both certificates already exist in `%USERPROFILE%\.aos\security` (`aos-user-oem.p12`, `aos-user-sp.p12`). You can check them with `aos-keys info --sp` and `aos-keys info --oem`.

## Before you start
- The drone Unit (AosVM) exists and is online in the OEM portal (**Units**). If not, see `AOS-Drones-PoC-impl-Plan.md`, stage B, step B1.
- `config.yaml` → `cmd` holds the host IP as seen from the AosVM (default `10.0.2.2`). Check it on the Unit with `ip route`.

## 1. Upload the Container (SP)
```powershell
cd C:\workspace\carla-air\aos-drones-poc\container
.\scripts\sign-and-upload.ps1
```
Expected output: `Certificate info: user=sp-...`, then `Deployment bundle successfully uploaded!`

In https://sp.aoscloud.io/sp → **Services**, the service **aos-drones-poc-container** now appears, version `0.1.0`.

Use `.\scripts\sign-and-upload.ps1 -SignOnly` to build and check `batch.tar.gz` without uploading.

## 2. Install the Service on the Unit (OEM)
In https://oem.aoscloud.io:
1. **Subjects → +**. Enter a label, e.g. `drone-poc`, then **Add**. Open the new subject.
2. **Services** tab → **Add service**. Select `aos-drones-poc-container`, then **Add**.
3. **Assigned unit** tab → **Add unit**. Search by the Unit's **System ID** (shown on the Unit page), then **Add**.

## 3. Verify
- In the OEM portal, open the Unit → **Subject & Services** → **Services**. `aos-drones-poc-container` shows as **active**.
- In the SP portal, go to **Service Logs → + → Service Log** and download the log when it's ready. It contains the `[drone SimpleFlight] ... NED ... GPS ...` lines.
- On the Windows host, the backend console (`container_backend\scripts\run-backend.ps1`) shows telemetry arriving from the AosVM address.

## Update / rollback
1. Raise `version` in `config.yaml` (e.g. `0.1.1`).
2. Repeat step 1. The Subject from step 2 stays as it is.
3. AosCloud rolls the new version out to the Unit.
