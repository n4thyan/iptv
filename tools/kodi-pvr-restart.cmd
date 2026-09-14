@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0kodi-pvr-healthcheck.ps1" -RestartPvrClient
if errorlevel 1 (
  echo.
  echo Kodi PVR restart failed. Check the message above.
  pause
)
endlocal
