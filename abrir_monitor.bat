@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  goto localizar_python
)
".venv\Scripts\python.exe" preparar_monitor.py
goto finalizar

:localizar_python
where py >nul 2>nul
if errorlevel 1 goto tentar_python
py -3 preparar_monitor.py
goto finalizar

:tentar_python
where python >nul 2>nul
if errorlevel 1 goto sem_python
python preparar_monitor.py
goto finalizar

:sem_python
echo Instale Python 3.11 ou mais recente pelo site https://www.python.org/downloads/
echo Marque a opcao Add Python to PATH e inclua Tcl/Tk na instalacao.
echo Depois abra este arquivo novamente.
pause
exit /b 2

:finalizar
if errorlevel 1 (
  echo.
  echo O monitor nao conseguiu abrir. A mensagem acima informa o problema.
  pause
  exit /b 2
)
