@echo off
echo =========================================
echo   AI-TwitterPersona Setup
echo =========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

echo [INFO] Python found: 
python --version

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo [INFO] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

REM Check if token.env exists
if not exist "token.env" (
    echo.
    echo [WARNING] token.env file not found
    echo Creating template token.env file...
    
    echo # Twitter API Keys >> token.env
    echo api_key=YOUR_TWITTER_API_KEY >> token.env
    echo api_secret=YOUR_TWITTER_API_SECRET >> token.env
    echo access_token=YOUR_ACCESS_TOKEN >> token.env
    echo access_token_secret=YOUR_ACCESS_TOKEN_SECRET >> token.env
    echo bearer_token=YOUR_BEARER_TOKEN >> token.env
    echo USER_ID=YOUR_TWITTER_USER_ID >> token.env
    echo. >> token.env
    echo # Google Gemini AI >> token.env
    echo gemini_api_key=YOUR_GEMINI_API_KEY >> token.env
    echo. >> token.env
    echo # Bot Configuration >> token.env
    echo TRENDS_LIMIT=3 >> token.env
    echo SLEEP_HOURS=1,3,9,10 >> token.env
    echo NIGHT_MODE_START=1 >> token.env
    echo NIGHT_MODE_END=6 >> token.env
    echo CYCLE_DURATION_MINUTES=60 >> token.env
    echo TRENDS_URL=https://xtrends.iamrohit.in/turkey >> token.env
    echo GEMINI_MODEL=gemini-2.5-flash >> token.env
    echo AI_TEMPERATURE=0.85 >> token.env
    echo DB_NAME=twitter.db >> token.env
    echo TABLE_NAME=tweets >> token.env
    echo. >> token.env
    echo # Web Dashboard Configuration >> token.env
    echo WEB_PORT=5000 >> token.env
    echo WEB_HOST=127.0.0.1 >> token.env
    echo WEB_DEBUG=False >> token.env
    echo FLASK_SECRET_KEY=twitter-bot-secret-key >> token.env
    echo ADMIN_USERS=admin >> token.env
    echo ADMIN_PASSWORD_HASH= >> token.env
    echo WORKERS=1 >> token.env
    
    echo [INFO] Template token.env file created
    echo [IMPORTANT] Please edit token.env and add your API keys!
    echo.
)

REM Initialize database
echo [INFO] Setting up database...
python database.py
if errorlevel 1 (
    echo [ERROR] Database setup failed
    pause
    exit /b 1
)

echo.
echo =========================================
echo   Setup Complete!
echo =========================================
echo.
echo Next steps:
echo 1. Edit token.env with your API keys
echo 2. Run start_bot.bat to start the CLI bot
echo 3. Run start_dashboard.bat to start the web dashboard
echo.
pause