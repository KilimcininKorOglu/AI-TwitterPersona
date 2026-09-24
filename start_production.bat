@echo off
echo =========================================
echo   AI-TwitterPersona Production Server
echo =========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo [ERROR] Virtual environment not found
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Gunicorn does not run on Windows (it needs fcntl and pwd), so production.py
REM serves the app with Flask-SocketIO on eventlet instead
python -c "import eventlet" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] eventlet not found. Run setup.bat first
    pause
    exit /b 1
)

REM Check configuration
if not exist "token.env" (
    echo [ERROR] token.env file not found
    pause
    exit /b 1
)

REM Initialize database
echo [INFO] Initializing database...
python database.py

REM Get configuration
for /f "tokens=2 delims==" %%a in ('findstr "WEB_PORT" token.env 2^>nul') do set WEB_PORT=%%a
for /f "tokens=2 delims==" %%a in ('findstr "WEB_HOST" token.env 2^>nul') do set WEB_HOST=%%a

if "%WEB_PORT%"=="" set WEB_PORT=8080
if "%WEB_HOST%"=="" set WEB_HOST=0.0.0.0

REM Start production server with single worker
echo [INFO] Starting Production Server...
echo [INFO] Server will be available at: http://%WEB_HOST%:%WEB_PORT%
echo [INFO] Running with SINGLE WORKER for bot state management
echo [INFO] Press Ctrl+C to stop the server
echo [INFO] If Ctrl+C doesn't work, close this window or press Ctrl+Break
echo.

REM Enable proper signal handling
set PYTHONUNBUFFERED=1
python production.py

echo.
echo [INFO] Production server stopped.
pause