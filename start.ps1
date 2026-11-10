# start.ps1 - starts the job-pipeline web app with one command.
#
#   powershell -ExecutionPolicy Bypass -File .\start.ps1
#
# Starts the API (FastAPI, this PC only, port 8000) in the background, then the
# frontend (Vite, port 5173) in this window. The frontend listens on the home
# network, so a phone on the same Wi-Fi can open the printed address; it forwards
# /api calls to the API, so the phone never needs to reach port 8000.
# Ctrl+C stops both.

$ErrorActionPreference = 'Stop'

$Root     = $PSScriptRoot
$Frontend = Join-Path $Root 'frontend'
$Python   = Join-Path $Root 'venv\Scripts\python.exe'
$ApiPort  = 8000
$WebPort  = 5173

# This PC's address on the home network: an adapter that is up and has a default
# gateway (the router), skipping virtual adapters (WSL, Hyper-V, VPNs). Wi-Fi first.
function Get-LanAddress {
    $virtual = 'vEthernet|WSL|Hyper-V|VirtualBox|VMware|Loopback|Tailscale|ZeroTier|Bluetooth'
    $configs = Get-NetIPConfiguration -ErrorAction SilentlyContinue | Where-Object {
        $_.IPv4DefaultGateway -and
        $_.IPv4Address -and
        $_.NetAdapter.Status -eq 'Up' -and
        $_.InterfaceAlias -notmatch $virtual
    }
    $best = $configs | Sort-Object { if ($_.InterfaceAlias -match 'Wi-?Fi|Wireless|WLAN') { 0 } else { 1 } } |
        Select-Object -First 1
    if ($best) { return @($best.IPv4Address)[0].IPAddress }
    return $null
}

function Test-PortOpen($port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $client.Connect('127.0.0.1', $port)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

if (-not (Test-Path $Python)) {
    Write-Host "No Python found at $Python. Create the venv first (see README.md)." -ForegroundColor Red
    exit 1
}
foreach ($port in $ApiPort, $WebPort) {
    if (Test-PortOpen $port) {
        Write-Host "Port $port is already in use. Is the app already running in another window?" -ForegroundColor Red
        exit 1
    }
}

if (-not (Test-Path (Join-Path $Frontend 'node_modules'))) {
    Write-Host 'frontend\node_modules is missing: running npm install (first time only)...'
    Push-Location $Frontend
    try {
        npm install
        if ($LASTEXITCODE -ne 0) { throw 'npm install failed' }
    } finally {
        Pop-Location
    }
}

# The API binds to 127.0.0.1 only: just Vite (on this PC) talks to it.
Write-Host "Starting the API on http://127.0.0.1:$ApiPort ..."
$api = Start-Process -FilePath $Python -WorkingDirectory $Root -NoNewWindow -PassThru `
    -ArgumentList '-m', 'uvicorn', 'api:app', '--host', '127.0.0.1', '--port', "$ApiPort"

try {
    # Wait until the API answers (up to 30 seconds)
    $deadline = (Get-Date).AddSeconds(30)
    while (-not (Test-PortOpen $ApiPort)) {
        if ($api.HasExited) { throw 'The API stopped while starting. See the error above.' }
        if ((Get-Date) -gt $deadline) { throw "The API did not start within 30 seconds." }
        Start-Sleep -Milliseconds 300
    }

    $lan = Get-LanAddress
    Write-Host ''
    Write-Host '======================================================'
    Write-Host "  On this PC:  http://localhost:$WebPort"
    if ($lan) {
        Write-Host "  On a phone:  http://${lan}:$WebPort" -ForegroundColor Green
        Write-Host '               (phone on the same Wi-Fi as this PC)'
    } else {
        Write-Host '  On a phone:  no home network address found (is Wi-Fi connected?)' -ForegroundColor Yellow
    }
    Write-Host '  Press Ctrl+C to stop the app.'
    Write-Host '======================================================'
    Write-Host 'If the phone cannot open the page, Windows Firewall may be blocking'
    Write-Host "port $WebPort. Allow Node.js when Windows asks, or see README.md."
    Write-Host ''

    # Run Vite directly with node (not npm.cmd), so Ctrl+C does not stop at
    # "Terminate batch job (Y/N)?"
    Push-Location $Frontend
    try {
        node (Join-Path $Frontend 'node_modules\vite\bin\vite.js')
    } finally {
        Pop-Location
    }
} finally {
    if (-not $api.HasExited) {
        Write-Host 'Stopping the API...'
        # /T also stops the child process the venv's python.exe launcher starts
        taskkill /PID $api.Id /T /F | Out-Null
    }
}
