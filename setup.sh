#!/bin/bash

# AI-TwitterPersona Linux Setup Script
# Usage: bash setup.sh [production]

set -e  # Exit on any error

echo "=========================================="
echo "   AI-TwitterPersona Linux Setup"
echo "=========================================="
echo

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "[ERROR] Don't run this script as root"
   exit 1
fi

# Check if Python 3.8+ is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed"
    echo "Install with: sudo apt-get update && sudo apt-get install python3 python3-pip python3-venv"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "[INFO] Python version: $PYTHON_VERSION"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "[INFO] Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "[INFO] Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies"
    exit 1
fi

# Check if production setup
if [[ "$1" == "production" ]]; then
    echo "[INFO] Setting up for PRODUCTION environment"
    
    # Install production dependencies
    pip install gunicorn supervisor
    
    # Copy production environment template
    if [ ! -f "token.env" ]; then
        cp .env.production token.env
        echo "[INFO] Created token.env from production template"
        echo "[IMPORTANT] Please edit token.env with your production API keys!"
    fi
    
    # Create user for running the service
    if ! id "twitterbot" &>/dev/null; then
        echo "[INFO] Creating twitterbot user..."
        sudo useradd --create-home --shell /bin/bash twitterbot
    fi
    
    # Set up systemd services
    echo "[INFO] Installing systemd services..."
    sudo cp twitter-bot.service /etc/systemd/system/
    sudo cp twitter-dashboard.service /etc/systemd/system/
    sudo systemctl daemon-reload
    
    echo "[INFO] Production setup complete!"
    echo "To start services: sudo systemctl enable --now twitter-bot twitter-dashboard"
    
else
    echo "[INFO] Setting up for DEVELOPMENT environment"
    
    # Copy development environment template
    if [ ! -f "token.env" ]; then
        cp .env.example token.env
        echo "[INFO] Created token.env from example template"
        echo "[IMPORTANT] Please edit token.env with your API keys!"
    fi
fi

# Initialize database
echo "[INFO] Setting up database..."
python database.py
if [ $? -ne 0 ]; then
    echo "[ERROR] Database setup failed"
    exit 1
fi

echo
echo "=========================================="
echo "   Setup Complete!"
echo "=========================================="
echo
echo "Next steps:"
echo "1. Edit token.env with your API keys"
if [[ "$1" == "production" ]]; then
    echo "2. sudo systemctl start twitter-bot twitter-dashboard"
    echo "3. Check status: sudo systemctl status twitter-dashboard"
else
    echo "2. Run: python main.py (for CLI bot)"
    echo "3. Run: python app.py (for web dashboard)"
fi
echo