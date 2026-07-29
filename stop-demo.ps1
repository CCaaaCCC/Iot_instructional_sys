# Smart Greenhouse Teaching System - Stop Service Script (Firewall Cleanup)
# Stops both backend (8001) and frontend (5173) services

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Smart Greenhouse System - Stop Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Stop backend service (Port 8001)
Write-Host "[1/3] Stopping backend service (Port 8001)..." -ForegroundColor Green
$backendConnections = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
if ($backendConnections) {
    $pids = $backendConnections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($pid in $pids) {
        try {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Write-Host "  OK - Process PID: $pid stopped" -ForegroundColor Green
        } catch {
            Write-Host "  FAIL - Cannot stop process PID: $pid" -ForegroundColor Red
        }
    }
} else {
    Write-Host "  - Backend service not running" -ForegroundColor Yellow
}

# Stop frontend service (Port 5173)
Write-Host "[2/3] Stopping frontend service (Port 5173)..." -ForegroundColor Green
$frontendConnections = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
if ($frontendConnections) {
    $pids = $frontendConnections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($pid in $pids) {
        try {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Write-Host "  OK - Process PID: $pid stopped" -ForegroundColor Green
        } catch {
            Write-Host "  FAIL - Cannot stop process PID: $pid" -ForegroundColor Red
        }
    }
} else {
    Write-Host "  - Frontend service not running" -ForegroundColor Yellow
}

# Stop MCP bridge (PID file, Start-Job, or raw Python process)
Write-Host "[3/4] Stopping MCP bridge..." -ForegroundColor Green
$stopped = $false
# Try PID file first
$pidFile = Join-Path (Get-Location) "mcp_bridge.pid"
if (Test-Path $pidFile) {
    $pid = Get-Content $pidFile -Raw -ErrorAction SilentlyContinue
    if ($pid) {
        try {
            Stop-Process -Id $([int]$pid.Trim()) -Force -ErrorAction SilentlyContinue
            Write-Host "  OK - MCP bridge PID: $($pid.Trim()) stopped" -ForegroundColor Green
            $stopped = $true
        } catch {}
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}
# Try Start-Job (for Start-Job based launch)
if (-not $stopped) {
    $mcpJob = Get-Job -Name "MCPBridge" -ErrorAction SilentlyContinue
    if ($mcpJob) {
        Stop-Job -Job $mcpJob -ErrorAction SilentlyContinue
        Remove-Job -Job $mcpJob -Force -ErrorAction SilentlyContinue
        Write-Host "  OK - MCP bridge job stopped" -ForegroundColor Green
        $stopped = $true
    }
}
# Fallback: kill raw Python process running mcp_bridge.py
if (-not $stopped) {
    $bridgePids = Get-CimInstance Win32_Process -Filter "Name='python.exe' AND CommandLine LIKE '%mcp_bridge%'" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessId
    if ($bridgePids) {
        foreach ($pid in $bridgePids) {
            try {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Write-Host "  OK - MCP bridge PID: $pid stopped" -ForegroundColor Green
            } catch {
                Write-Host "  FAIL - Cannot stop MCP bridge PID: $pid" -ForegroundColor Red
            }
        }
        $stopped = $true
    }
}
if (-not $stopped) {
    Write-Host "  - MCP bridge not running" -ForegroundColor Yellow
}

# Cleanup firewall rules (optional, kept for quick restart convenience)
Write-Host "[4/4] Cleaning up firewall rules..." -ForegroundColor Green
$ruleGroup = "SmartGreenhouseDemo"
try {
    Remove-NetFirewallRule -DisplayGroup $ruleGroup -ErrorAction Stop
    Write-Host "  OK - Firewall rules removed" -ForegroundColor Green
} catch {
    Write-Host "  - No firewall rules to cleanup" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Services stopped successfully" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To start services: .\start-demo.ps1" -ForegroundColor Gray
Write-Host ""
