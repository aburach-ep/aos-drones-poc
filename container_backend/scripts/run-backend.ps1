<#
.SYNOPSIS
  Start the AOS-Drones-PoC Container backend on the Windows host.
.EXAMPLE
  .\run-backend.ps1                         # 0.0.0.0:8080
  .\run-backend.ps1 -BindHost 127.0.0.1     # local-only
#>
param(
    [string]$BindHost  = "0.0.0.0",
    [int]   $Port      = 8080,
    [string]$PythonExe = "python"
)
$ErrorActionPreference = "Stop"
& $PythonExe -u (Join-Path $PSScriptRoot "..\backend.py") --host $BindHost --port $Port
