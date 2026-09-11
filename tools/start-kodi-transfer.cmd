@echo off
setlocal
set "SCRIPT=%~dp0prepare-kodi-transfer.ps1"
echo Starting the temporary Kodi transfer share with Administrator rights...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"\"%SCRIPT%\"\" -CreateShare'"
if errorlevel 1 (
  echo Failed to request Administrator access.
  pause
)
endlocal
