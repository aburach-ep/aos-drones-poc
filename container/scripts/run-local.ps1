<#
.SYNOPSIS
  Run the AOS-Drones-PoC Container natively on Windows against local CARLA-Air.
.EXAMPLE
  .\run-local.ps1
  .\run-local.ps1 -BackendUrl "" -PollInterval 0.5     # no backend, faster polling
#>
param(
    [string]$AirSimHost   = "127.0.0.1",
    [int]   $AirSimPort   = 41451,
    [int]   $CarlaPort    = 2000,
    [string]$VehicleName  = "SimpleFlight",
    [double]$PollInterval = 1.0,
    [string]$BackendUrl   = "http://127.0.0.1:8080/telemetry",
    [string]$DroneId      = "drone-local-01",
    [string]$PythonExe    = "python"
)
$ErrorActionPreference = "Stop"
$src = Join-Path $PSScriptRoot "..\drone-telemetry\src_any" | Resolve-Path

Push-Location $src
try {
    & $PythonExe -u main.py `
        --airsim-host $AirSimHost --airsim-port $AirSimPort --carla-port $CarlaPort `
        --vehicle-name $VehicleName --poll-interval $PollInterval `
        --backend-url $BackendUrl --drone-id $DroneId
} finally {
    Pop-Location
}
