@echo off
setlocal
cd /d "%~dp0"
set "PYTHON_CMD="
set "EMBEDDED_PY=%USERPROFILE%\Downloads\ComfyUI_windows_portable_nvidia_cu126\ComfyUI_windows_portable\python_embeded\python.exe"

if exist ".venv\Scripts\python.exe" set "PYTHON_CMD=%CD%\.venv\Scripts\python.exe"
if not defined PYTHON_CMD (
  py -3 -c "import sys" >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
  python -c "import sys" >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD if exist "%EMBEDDED_PY%" (
  set "PYTHON_CMD=%EMBEDDED_PY%"
  set "EMBEDDED_MODE=1"
)
if not defined PYTHON_CMD (
  echo Python 3.10 or newer is required. Install it from https://www.python.org/downloads/
  echo During setup, select "Add python.exe to PATH", then run this file again.
  pause
  exit /b 1
)

if not defined EMBEDDED_MODE if not exist ".venv\Scripts\python.exe" (
  echo Creating a local Python environment...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 goto :failed
  set "PYTHON_CMD=%CD%\.venv\Scripts\python.exe"
)

if defined EMBEDDED_MODE (
  if not exist ".runtime" mkdir .runtime
  echo Installing dependencies for this app...
  "%PYTHON_CMD%" -m pip install --disable-pip-version-check --upgrade --target .runtime -r requirements.txt
  if errorlevel 1 goto :failed
) else (
  echo Installing or checking app dependencies...
  "%PYTHON_CMD%" -m pip install --disable-pip-version-check -r requirements.txt
  if errorlevel 1 goto :failed
)

set "API_URL=http://127.0.0.1:8000"
start "Aurlex Insights API" cmd /k ""%PYTHON_CMD%" app_launcher.py api"
timeout /t 3 /nobreak >nul
start "Aurlex Insights Dashboard" cmd /k ""%PYTHON_CMD%" app_launcher.py ui"
timeout /t 5 /nobreak >nul
start "" http://127.0.0.1:8501
exit /b 0

:failed
echo Setup failed. Check the error above and confirm Python and internet access are available.
pause
exit /b 1


