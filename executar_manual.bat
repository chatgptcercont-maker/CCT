@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Prepare o ambiente conforme GUIA_MONITOR.md antes de executar.
  exit /b 2
)
".venv\Scripts\python.exe" monitor.py %*
exit /b %errorlevel%
