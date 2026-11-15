@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" run_atlantis.py
) else (
  py -3.12 run_atlantis.py
)
if errorlevel 1 (
  echo ATLANTIS could not start. Run install_windows.bat first.
  pause
)
