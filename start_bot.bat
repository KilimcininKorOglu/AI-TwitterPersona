@echo off
echo =========================================
echo   AI-TwitterPersona Bot Starter
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

REM Check if requirements are installed
echo [INFO] Checking dependencies...
python -c "import tweepy, google.generativeai" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Dependencies not found. Installing...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Initialize database
echo [INFO] Initializing database...
python database.py
if errorlevel 1 (
    echo [ERROR] Database initialization failed
    pause
    exit /b 1
)

REM Start the bot
echo [INFO] Starting AI-TwitterPersona Bot...
echo [INFO] Press Ctrl+C to stop the bot
echo [INFO] If Ctrl+C doesn't work, close this window or press Ctrl+Break
echo.

REM Enable Ctrl+C handling for Python
set PYTHONUNBUFFERED=1
python main.py

echo.
echo [INFO] Bot stopped.
pause