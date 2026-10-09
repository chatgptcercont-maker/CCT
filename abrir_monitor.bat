@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Prepare o ambiente conforme GUIA_MONITOR.md antes de abrir o monitor.
  pause
  exit /b 2
)
".venv\Scripts\python.exe" interface.py
if errorlevel 1 pause
