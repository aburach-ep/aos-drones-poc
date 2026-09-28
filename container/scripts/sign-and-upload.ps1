<#
.SYNOPSIS
  Service Provider step: sign the Container bundle and upload it to AosCloud.
.DESCRIPTION
  Uses the AOS host tools installed in C:\workspace\carla-air\aos (aos-signer 2.0.2)
  and the SP user certificate %USERPROFILE%\.aos\security\aos-user-sp.p12
  (created once with: aos-keys new-user -d aoscloud.io -t <SP token> --sp).
.EXAMPLE
  .\sign-and-upload.ps1            # sign and upload
  .\sign-and-upload.ps1 -SignOnly  # only build/sign the bundle locally
#>
param(
    [string]$AosToolsDir = "C:\workspace\carla-air\aos",
    [switch]$SignOnly
)
$ErrorActionPreference = "Stop"
$containerDir = Join-Path $PSScriptRoot ".." | Resolve-Path

. (Join-Path $AosToolsDir "aos-env.ps1")

$spCert = Join-Path $env:USERPROFILE ".aos\security\aos-user-sp.p12"
if (-not (Test-Path $spCert)) {
    throw "SP certificate not found: $spCert. Run: aos-keys new-user -d aoscloud.io -t <SP token> --sp"
}

Push-Location $containerDir
try {
    Write-Host "Signing bundle in $containerDir ..."
    aos-signer sign
    if ($LASTEXITCODE -ne 0) { throw "aos-signer sign failed" }
    if (-not $SignOnly) {
        Write-Host "Uploading to AosCloud ..."
        aos-signer upload
        if ($LASTEXITCODE -ne 0) { throw "aos-signer upload failed" }
        Write-Host "Done. Next (OEM portal https://oem.aoscloud.io): Subjects -> + -> add service 'aos-drones-poc-container' -> assign the drone Unit. See PUBLISH.md."
    }
} finally {
    Pop-Location
}
