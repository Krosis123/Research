@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install -r requirements-integrated.lock.txt
if errorlevel 1 goto failed
echo Installation complete. Run launch_atlantis.bat.
pause
exit /b 0
:failed
echo Installation failed. See the messages above.
pause
exit /b 1
