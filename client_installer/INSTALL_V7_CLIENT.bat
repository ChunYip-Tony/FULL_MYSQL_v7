@echo off
setlocal EnableExtensions
set "TARGET=C:\FULL_MYSQL\FULL_MYSQL_Seafood_Client_v7"
set "PAYLOAD=%~dp0payload"
echo ============================================================
echo   FULL MYSQL Seafood Client v7.0.1 - HTTPS Installer
echo ============================================================
echo.
if not exist "%TARGET%" mkdir "%TARGET%"
robocopy "%PAYLOAD%" "%TARGET%" /E /R:2 /W:1 >nul
if errorlevel 8 (
  echo [ERROR] Could not copy application files.
  pause & exit /b 1
)
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY (
  echo [ERROR] Python 3.12+ is required. Install Python, then rerun this installer.
  pause & exit /b 2
)
cd /d "%TARGET%"
if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv || (echo [ERROR] Could not create venv.& pause & exit /b 3)
)
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt || (echo [ERROR] Dependency install failed.& pause & exit /b 4)
.venv\Scripts\python.exe -m py_compile config.py api_client.py configure_api.py agent.py dashboard.py || (echo [ERROR] Compile test failed.& pause & exit /b 5)
echo.
echo Installed to: %TARGET%
echo Next: run CONFIGURE_API.bat after the DigitalOcean Secure API is deployed.
echo Then run START_CLIENT.bat.
pause
