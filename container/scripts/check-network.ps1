<#
.SYNOPSIS
  Check that CARLA-Air (AirSim 41451, CARLA 2000) and the Container backend (8080)
  listen on an address reachable from the AosVM (0.0.0.0 / host IP, not only 127.0.0.1).
.EXAMPLE
  .\check-network.ps1
  .\check-network.ps1 -AddFirewallRules    # run as Administrator
#>
param(
    [int[]]$Ports = @(41451, 2000, 8080),
    [switch]$AddFirewallRules
)

foreach ($port in $Ports) {
    $listen = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
    if (-not $listen) {
        Write-Host ("{0,-6} NOT LISTENING" -f $port) -ForegroundColor Red
        continue
    }
    foreach ($l in $listen) {
        $proc = (Get-Process -Id $l.OwningProcess -ErrorAction SilentlyContinue).ProcessName
        $reachable = $l.LocalAddress -notin @("127.0.0.1", "::1")
        $color = if ($reachable) { "Green" } else { "Yellow" }
        $note  = if ($reachable) { "reachable from VM (subject to firewall)" } else { "loopback only - VM cannot reach it" }
        Write-Host ("{0,-6} {1,-15} {2,-20} {3}" -f $port, $l.LocalAddress, $proc, $note) -ForegroundColor $color
    }
}

if ($AddFirewallRules) {
    foreach ($port in $Ports) {
        $name = "AOS-Drones-PoC TCP $port"
        if (-not (Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue)) {
            New-NetFirewallRule -DisplayName $name -Direction Inbound -Protocol TCP -LocalPort $port -Action Allow | Out-Null
            Write-Host "Added firewall rule: $name"
        }
    }
} else {
    Write-Host "`nTip: run with -AddFirewallRules (as Administrator) to allow inbound TCP $($Ports -join ', ') from the AosVM."
}
