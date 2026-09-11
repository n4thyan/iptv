@echo off
setlocal

net session >nul 2>&1
if not "%errorlevel%"=="0" (
  echo Requesting Administrator access...
  powershell.exe -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

echo Preparing the temporary Kodi SMB transfer share...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0prepare-kodi-transfer.ps1" -CreateShare

echo.
echo Leave this window open while copying files between the PC and Kodi.
echo You can close it after the transfer; the share itself can be removed with stop-kodi-transfer.cmd.
pause
endlocal
