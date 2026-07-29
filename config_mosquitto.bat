@echo off
REM Mosquitto LAN access config - auto elevate to admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Need admin rights, elevating...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)
echo Running mosquitto configuration...
powershell -NoProfile -ExecutionPolicy Bypass -File "d:\IoT\configure_mosquitto.ps1"
echo.
echo Done. Check output above.
pause
