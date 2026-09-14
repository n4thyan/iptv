@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0kodi-pvr-demo-workaround.ps1"
if errorlevel 1 (
  echo.
  echo Kodi Demo PVR workaround did not complete successfully. Check the message above.
  pause
)
endlocal
