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

REM Check if Gunicorn is installed
python -c "import gunicorn" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Gunicorn not found. Installing...
    pip install gunicorn
    if errorlevel 1 (
        echo [ERROR] Failed to install Gunicorn
        pause
        exit /b 1
    )
)

REM Check configuration
if not exist "token.env" (
    echo [ERROR] token.env file not found
    pause
    exit /b 1
)

if not exist "gunicorn.conf.py" (
    echo [ERROR] gunicorn.conf.py file not found
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
gunicorn --config gunicorn.conf.py app:app --workers=1 --bind=%WEB_HOST%:%WEB_PORT%

echo.
echo [INFO] Production server stopped.
pause