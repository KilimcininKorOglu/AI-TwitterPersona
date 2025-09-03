@echo off
echo =========================================
echo   AI-TwitterPersona Web Dashboard
echo =========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python and add it to your PATH
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

REM Check if token.env exists
if not exist "token.env" (
    echo [ERROR] token.env file not found
    echo Please create token.env file with your API keys
    pause
    exit /b 1
)

REM Check if Flask dependencies are installed
echo [INFO] Checking web dependencies...
python -c "import flask, flask_socketio, flask_login" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Web dependencies not found. Installing...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
)

echo [INFO] Note: Dashboard will start even without API keys configured
echo [INFO] You can configure API keys through the web interface

REM Initialize database
echo [INFO] Initializing database...
python database.py
if errorlevel 1 (
    echo [ERROR] Database initialization failed
    pause
    exit /b 1
)

REM Get web configuration
for /f "tokens=2 delims==" %%a in ('findstr "WEB_PORT" token.env 2^>nul') do set WEB_PORT=%%a
for /f "tokens=2 delims==" %%a in ('findstr "WEB_HOST" token.env 2^>nul') do set WEB_HOST=%%a

REM Set defaults if not found
if "%WEB_PORT%"=="" set WEB_PORT=5000
if "%WEB_HOST%"=="" set WEB_HOST=127.0.0.1

REM Start the web dashboard
echo [INFO] Starting Web Dashboard...
echo [INFO] Dashboard will be available at: http://%WEB_HOST%:%WEB_PORT%
echo [INFO] Press Ctrl+C to stop the dashboard
echo [INFO] If Ctrl+C doesn't work, close this window or press Ctrl+Break
echo.

REM Enable Ctrl+C handling for Python
set PYTHONUNBUFFERED=1
python app.py

echo.
echo [INFO] Dashboard stopped.
pause