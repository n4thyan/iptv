@echo off
setlocal

net session >nul 2>&1
if not "%errorlevel%"=="0" (
  echo Requesting Administrator access...
  powershell.exe -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

echo Removing the temporary Kodi SMB transfer share...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0prepare-kodi-transfer.ps1" -RemoveShare
pause
endlocal
