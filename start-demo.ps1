# Smart Greenhouse Teaching System - Demo Startup Script (LAN Access Enabled)
# Starts both backend (8001) and frontend (5173) services

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Smart Greenhouse System - Demo Mode" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get local LAN IP - prefer default route interface, fallback to filtering virtual adapters
$localIP = $null
$defaultRoute = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | Sort-Object RouteMetric | Select-Object -First 1
if ($defaultRoute) {
    $localIP = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $defaultRoute.ifIndex -ErrorAction SilentlyContinue | Select-Object -First 1).IPAddress
}
# Fallback: filter common virtual adapter subnets (VirtualBox/Hyper-V/WSL2/libvirt)
if (-not $localIP) {
    $allIPs = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notmatch '^(127\.|169\.254\.|192\.168\.56\.|192\.168\.99\.|192\.168\.122\.|172\.17\.|10\.0\.2\.)' -and $_.PrefixOrigin -ne 'WellKnown' }
    $localIP = ($allIPs | Select-Object -First 1).IPAddress
}
if (-not $localIP) {
    $localIP = "127.0.0.1"
    Write-Host "[WARN] LAN IP not detected, local access only" -ForegroundColor Yellow
} else {
    Write-Host "[INFO] Local LAN IP: $localIP" -ForegroundColor Gray
}
Write-Host ""

# Configure Windows Firewall (allow ports)
$backendPort = 8001
$frontendPort = 5173
$ruleGroup = "SmartGreenhouseDemo"

try {
    # Remove old rules if exist
    Remove-NetFirewallRule -DisplayGroup $ruleGroup -ErrorAction SilentlyContinue
    
    # Add new rules
    New-NetFirewallRule -DisplayName "Backend API (Port $backendPort)" -Direction Inbound -Protocol TCP -LocalPort $backendPort -Action Allow -DisplayGroup $ruleGroup -ErrorAction Stop | Out-Null
    New-NetFirewallRule -DisplayName "Frontend Web (Port $frontendPort)" -Direction Inbound -Protocol TCP -LocalPort $frontendPort -Action Allow -DisplayGroup $ruleGroup -ErrorAction Stop | Out-Null
    Write-Host "[FIREWALL] Ports $backendPort and $frontendPort opened" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Firewall config failed (requires admin), please manually open ports" -ForegroundColor Yellow
    Write-Host "  Manual cmd: New-NetFirewallRule -DisplayName 'SmartGreenhouse' -Direction Inbound -Protocol TCP -LocalPort 8001,5173 -Action Allow" -ForegroundColor Yellow
}
Write-Host ""

# Check if backend port is in use
$backendPortInUse = Get-NetTCPConnection -LocalPort $backendPort -ErrorAction SilentlyContinue
if ($backendPortInUse) {
    Write-Host "[WARN] Port $backendPort is in use, service may already be running" -ForegroundColor Yellow
    Write-Host "  To restart, run: .\stop-demo.ps1" -ForegroundColor Yellow
    Write-Host ""
}

# Check if frontend port is in use
$frontendPortInUse = Get-NetTCPConnection -LocalPort $frontendPort -ErrorAction SilentlyContinue
if ($frontendPortInUse) {
    Write-Host "[WARN] Port $frontendPort is in use, service may already be running" -ForegroundColor Yellow
    Write-Host "  To restart, run: .\stop-demo.ps1" -ForegroundColor Yellow
    Write-Host ""
}

# Start backend service (bind to 0.0.0.0 for LAN access)
Write-Host "[1/2] Starting backend service (0.0.0.0:$backendPort)..." -ForegroundColor Green
$backendJob = Start-Process -FilePath "uvicorn" -ArgumentList "app.main:app", "--reload", "--host", "0.0.0.0", "--port", $backendPort -WindowStyle Minimized -PassThru
Start-Sleep -Seconds 3

# Check if backend started successfully
$backendStarted = Get-NetTCPConnection -LocalPort $backendPort -ErrorAction SilentlyContinue
if ($backendStarted) {
    Write-Host "  OK - Backend started (listening on 0.0.0.0:$backendPort)" -ForegroundColor Green
} else {
    Write-Host "  FAIL - Backend startup failed, check logs" -ForegroundColor Red
    exit 1
}

# Start frontend service (Vite configured with host: '0.0.0.0')
Write-Host "[2/3] Starting frontend service (0.0.0.0:$frontendPort)..." -ForegroundColor Green
$frontendJob = Start-Process -FilePath "npm" -ArgumentList "run", "dev" -WorkingDirectory "frontend" -WindowStyle Minimized -PassThru
Start-Sleep -Seconds 3

# Check if frontend started successfully
$frontendStarted = Get-NetTCPConnection -LocalPort $frontendPort -ErrorAction SilentlyContinue
if ($frontendStarted) {
    Write-Host "  OK - Frontend started (listening on 0.0.0.0:$frontendPort)" -ForegroundColor Green
} else {
    Write-Host "  FAIL - Frontend startup failed, check logs" -ForegroundColor Red
    exit 1
}

# Start MCP bridge (小智 AI 工具调用桥接, using .NET Process for full detachment)
Write-Host "[3/3] Starting MCP bridge (ESP32-S3 小智 AI)..." -ForegroundColor Green
$mcpBridgeLog = Join-Path (Get-Location) "mcp_bridge.log"
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "$(Get-Location)\.venv\Scripts\python.exe"
$psi.Arguments = "mcp_bridge.py"
$psi.WorkingDirectory = "$(Get-Location)"
$psi.UseShellExecute = $true   # detached process, survives sandbox
$psi.CreateNoWindow = $true
$psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
$mcpBridgeProc = [System.Diagnostics.Process]::Start($psi)
Start-Sleep -Seconds 3
# Check if bridge process is still running (not exited immediately)
if ($mcpBridgeProc -and !$mcpBridgeProc.HasExited) {
    Write-Host "  OK - MCP bridge started (PID: $($mcpBridgeProc.Id), log: mcp_bridge.log)" -ForegroundColor Green
} else {
    Write-Host "  WARN - MCP bridge may not have started, check mcp_bridge.log" -ForegroundColor Yellow
}
# Save PID for stop-demo.ps1 to find later
$mcpBridgeProc.Id | Out-File -FilePath (Join-Path (Get-Location) "mcp_bridge.pid") -Encoding ASCII -Force

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Services started successfully!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[LOCAL ACCESS]" -ForegroundColor White
Write-Host "  Frontend: http://localhost:$frontendPort" -ForegroundColor Yellow
Write-Host "  Backend API: http://localhost:$backendPort" -ForegroundColor Yellow
Write-Host "  API Docs: http://localhost:$backendPort/docs" -ForegroundColor Yellow
Write-Host ""
if ($localIP -ne "127.0.0.1") {
    Write-Host "[LAN ACCESS] Other devices on the same network can access:" -ForegroundColor White
    Write-Host "  Frontend: http://$localIP`:$frontendPort" -ForegroundColor Yellow
    Write-Host "  Backend API: http://$localIP`:$backendPort" -ForegroundColor Yellow
    Write-Host "  API Docs: http://$localIP`:$backendPort/docs" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Note: Access frontend page only, API requests are proxied by Vite" -ForegroundColor Gray
    Write-Host ""
}
Write-Host "[MCP BRIDGE] 小智 AI 工具调用桥接:" -ForegroundColor White
Write-Host "  Log: mcp_bridge.log (tail -f to monitor)" -ForegroundColor Yellow
Write-Host "  Status: Use '小智 AI' voice to query/control smart greenhouse" -ForegroundColor Yellow
Write-Host ""
Write-Host "Demo accounts:" -ForegroundColor White
Write-Host "  Admin: admin / Admin123456" -ForegroundColor Cyan
Write-Host "  Teacher: teacher / Teacher123456" -ForegroundColor Cyan
Write-Host "  Student: g1s1 / Student123456" -ForegroundColor Cyan
Write-Host ""
Write-Host "To stop services: .\stop-demo.ps1" -ForegroundColor Gray
Write-Host ""
