@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0kodi-url-helper.ps1"
if errorlevel 1 (
  echo.
  echo Kodi URL helper failed. Check the message above.
  pause
)
endlocal
