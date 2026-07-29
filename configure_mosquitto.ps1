# Configure mosquitto to allow LAN access (for ESP32-S3 hardware)
# Requires admin privileges
$logPath = "d:\IoT\mosquitto_config.log"
Start-Transcript -Path $logPath -Force | Out-Null

try {
    $configPath = "C:\Program Files\mosquitto\mosquitto.conf"

    $existing = Get-Content $configPath -Raw
    if ($existing -match "listener 1883 0\.0\.0\.0") {
        Write-Output "Already configured: listener 1883 0.0.0.0 exists, skipping"
    } else {
        Copy-Item $configPath "$configPath.bak" -Force
        Write-Output "Backed up original config to $configPath.bak"

        $addition = @"

# =================================================================
# Smart greenhouse upper computer MQTT config (allow LAN ESP32-S3)
# Added: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
# =================================================================
listener 1883 0.0.0.0
allow_anonymous true
"@
        Add-Content -Path $configPath -Value $addition
        Write-Output "Added: listener 1883 0.0.0.0 + allow_anonymous true"
    }

    Restart-Service -Name mosquitto -Force
    Start-Sleep -Seconds 2

    $svc = Get-Service mosquitto
    Write-Output "mosquitto service status: $($svc.Status)"

    $listening = Get-NetTCPConnection -LocalPort 1883 -State Listen -ErrorAction SilentlyContinue
    Write-Output "Port 1883 listening:"
    $listening | Select-Object LocalAddress, LocalPort, State | Format-Table -AutoSize | Out-String | Write-Output

    Write-Output "=== Configuration complete ==="
    Write-Output "ESP32-S3 can now connect via LAN IP on port 1883"

    # Add Windows Firewall rule for port 1883 (if not exists)
    $fwRule = Get-NetFirewallRule -DisplayName "Mosquitto MQTT (1883)" -ErrorAction SilentlyContinue
    if ($fwRule) {
        Write-Output "Firewall rule 'Mosquitto MQTT (1883)' already exists, skipping"
    } else {
        New-NetFirewallRule -DisplayName "Mosquitto MQTT (1883)" `
            -Direction Inbound -Protocol TCP -LocalPort 1883 `
            -Action Allow -Profile Any | Out-Null
        Write-Output "Added firewall rule: Mosquitto MQTT (1883) Inbound TCP Allow"
    }
} catch {
    Write-Output "ERROR: $_"
    Write-Output $_.Exception.Message
} finally {
    Stop-Transcript | Out-Null
}
