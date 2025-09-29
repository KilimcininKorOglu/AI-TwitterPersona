# 🤖 AI-TwitterPersona

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Security](https://img.shields.io/badge/security-fixed%2025%2F25-brightgreen.svg)](bugs.md)

Professional Twitter automation bot that tracks real-time trending topics in Turkey and generates personalized tweets using Google Gemini AI.

## ✨ Features

### 🤖 Smart Bot Features

- **📈 Live Trend Tracking**: Automatically fetches current trending topics from Turkey
- **🧠 AI Tweet Generation**: Natural, engaging tweets with Google Gemini 2.5 Flash
- **🎭 Dynamic Persona System**: 3 different writing styles based on topic
- **⏰ Smart Scheduling**: Configurable cycles and sleep hours
- **🔄 Auto Retry**: Intelligent retry mechanism on errors
- **💾 Cache System**: Topic cache to minimize API calls

### 🌐 Web Dashboard

- **📊 Real-time Monitoring**: Live bot status with WebSocket
- **⏱️ Dynamic Countdown**: Live counter for next tweet
- **🎛️ Full Control**: Start/stop bot, manual tweets
- **✨ AI Enhancement**: Improve written tweets with AI
- **📈 Detailed Analytics**: Success rates, persona usage, hourly activity
- **🔧 Live Configuration**: Edit settings via web interface
- **📝 Prompt Editor**: Edit persona prompts from web

### 🔒 Security & Stability

- **✅ Production Ready**: All 25 security vulnerabilities fixed
- **🔐 Authentication**: Secure encryption with bcrypt
- **🛡️ CSRF Protection**: Active on all POST endpoints
- **🔄 Thread Safety**: Proper locking mechanism for SQLite
- **📊 Rate Limiting**: API limit management

## 📋 System Requirements

| Requirement | Version/Details |
|-------------|-----------------|
| Python | 3.8+ |
| OS | Windows/Linux/macOS |
| RAM | Minimum 512MB |
| Disk | 100MB free space |
| Twitter API | [Developer Account](https://developer.x.com) |
| Gemini API | [Google AI Studio](https://ai.google.dev) |

## 🚀 Quick Start

### Windows Auto Setup (Recommended)

```batch
# 1. Complete setup (venv + dependencies + database)
setup.bat

# 2. Add API keys to token.env file

# 3. Start the bot
start_bot.bat

# 4. Open dashboard (optional)
start_dashboard.bat
```

### Manual Setup

```bash
# 1. Clone the repository
git clone https://github.com/KilimcininKorOglu/AI-TwitterPersona.git
cd AI-TwitterPersona

# 2. Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate.bat
# Linux/Mac:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create database
python database.py

# 5. Configure token.env file (see below)

# 6. Start the bot
python main.py

# 7. Web Dashboard (optional)
python app.py
```

## ⚙️ Configuration

### token.env File

Create a `token.env` file and add the following information:

```env
# ============ REQUIRED SETTINGS ============

# Twitter API Credentials
# Get from https://developer.x.com/en/portal/dashboard
api_key=YOUR_TWITTER_API_KEY
api_secret=YOUR_TWITTER_API_SECRET
access_token=YOUR_ACCESS_TOKEN
access_token_secret=YOUR_ACCESS_TOKEN_SECRET
bearer_token=YOUR_BEARER_TOKEN
USER_ID=YOUR_TWITTER_USER_ID  # https://tweeterid.com

# Google Gemini API
# Get from https://ai.google.dev
gemini_api_key=YOUR_GEMINI_API_KEY

# ============ BOT SETTINGS (Optional) ============

# Trend Settings
TRENDS_URL=https://xtrends.iamrohit.in/turkey
TRENDS_LIMIT=5

# Scheduling (hour format)
SLEEP_HOURS=1,2,3,4,5,6  # Hours when bot sleeps
CYCLE_DURATION_MINUTES=30  # Tweet interval

# AI Model Settings
GEMINI_MODEL=gemini-2.5-flash
AI_TEMPERATURE=1.0
AI_TOP_P=0.9
AI_TOP_K=40

# ============ WEB DASHBOARD (Optional) ============

# Flask Settings
FLASK_SECRET_KEY=your-very-secure-secret-key-here
WEB_HOST=127.0.0.1
WEB_PORT=5000
WEB_DEBUG=False

# Admin Login
ADMIN_USERS=admin
ADMIN_PASSWORD=admin123  # Change on first login!
```

## 🎮 Usage

### CLI Bot Mode

```bash
python main.py
```

When bot starts:

1. ⏰ Checks the time (outside sleep hours)
2. 📊 Fetches Turkey trends
3. 🎯 Classifies topic with AI
4. ✍️ Creates tweet with appropriate persona
5. 📤 Posts to Twitter
6. 💾 Saves to database
7. ⏳ Waits 30 minutes and repeats

### Web Dashboard

```bash
python app.py
# In browser: http://localhost:5000
```

#### Dashboard Features

| Page | URL | Features |
|------|-----|----------|
| **Homepage** | `/` | Bot status, statistics, countdown |
| **Tweet History** | `/tweets` | All tweets, filtering, resend |
| **Manual Tweet** | `/manual` | AI-powered tweet creation |
| **Monitoring** | `/monitoring` | Real-time console, API status |
| **Analytics** | `/analytics` | Charts, success rates |
| **Settings** | `/config` | Live configuration editing |
| **Prompt Editor** | `/prompts` | Edit persona prompts |

## 🎭 Persona System

The bot automatically uses 3 different personas based on topic:

### 💻 Tech Persona

- **Usage**: Technology, science, innovation topics
- **Style**: Confident, analytical, visionary
- **Example**: "AI revolution isn't coming—it's here. Adapt or get left behind 🚀"

### 😊 Casual Persona

- **Usage**: Daily, entertainment, social topics
- **Style**: Friendly, fun, Istanbul-based character
- **Example**: "Monday blues hitting different today... Already on coffee #3 ☕"

### 😔 Sad Persona

- **Usage**: Sad news, disasters, serious topics
- **Style**: Empathetic, respectful, comforting
- **Example**: "Our hearts go out to everyone affected... Stay strong 🙏"

## 📊 Example Console Output

```
[+] Starting bot...
[+] Twitter client ready
[+] Gemini AI connected
[+] Database ready

[10:30:00] Fetching trending topics...
  1. #AI (45K Tweets)
  2. #Technology (23K Tweets)
  3. #Innovation (18K Tweets)

[10:30:05] Selected topic: #AI
[10:30:06] AI classification: tech
[10:30:08] Tweet generated (275/280 characters)
[10:30:10] ✅ Tweet posted successfully!
[10:30:11] Saved to database (ID: 42)

⏳ Next tweet: 30 minutes (11:00:00)
29:59... 29:58... 29:57...
```

## 🧪 Testing & Validation

```bash
# Component tests
python -c "import database; database.createDatabase()"  # DB test
python -c "import trend; print(trend.prepareTrend(3))"  # Trend test
python -c "import twitter_client; twitter_client.get_client()"  # API test

# Configuration validation
python -c "from app import test_twitter_length_calculation; test_twitter_length_calculation()"

# Turkish character test
python -c "from trend import test_turkish_character_filtering; test_turkish_character_filtering()"
```

## 🚀 Production Deployment

### Gunicorn Deployment

```bash
# IMPORTANT: Only use single worker!
gunicorn --config gunicorn.conf.py app:app --workers=1
```

### Systemd Service

```bash
# Bot service
sudo cp twitter-bot.service /etc/systemd/system/
sudo systemctl enable twitter-bot
sudo systemctl start twitter-bot

# Dashboard service
sudo cp twitter-dashboard.service /etc/systemd/system/
sudo systemctl enable twitter-dashboard
sudo systemctl start twitter-dashboard
```

### Docker Deployment

```bash
# Build & Run
docker-compose up -d

# Watch logs
docker-compose logs -f
```

## 📁 Project Structure

```
AI-TwitterPersona/
├── 🤖 Core Bot Logic
│   ├── main.py              # Main bot loop and scheduling
│   ├── reply.py             # AI tweet generation and persona management
│   ├── trend.py             # Trend topic scraping
│   ├── twitter_client.py    # Twitter API client
│   └── database.py          # SQLite database operations
│
├── 🌐 Web Interface
│   ├── app.py               # Flask + SocketIO application
│   ├── templates/
│   │   ├── dashboard.html   # Main control panel
│   │   ├── manual.html      # Manual tweet page
│   │   ├── monitoring.html  # Real-time monitoring
│   │   └── analytics.html   # Statistics charts
│   └── static/
│       ├── js/app.js        # WebSocket and AJAX
│       └── css/style.css    # Custom styles
│
├── ⚙️ Configuration
│   ├── config.py            # Central configuration management
│   ├── token.env            # API keys and settings (gitignore)
│   ├── requirements.txt     # Python dependencies
│   └── topic_cache.json     # AI classification cache
│
├── 🚀 Deployment
│   ├── production.py        # WSGI production config
│   ├── gunicorn.conf.py     # Gunicorn settings
│   ├── Dockerfile           # Container image
│   ├── docker-compose.yml   # Multi-service orchestration
│   └── *.service           # Systemd unit files
│
└── 📝 Documentation
    ├── README.md            # Turkish readme
    ├── README.en.md         # This file
    ├── CLAUDE.md           # Guide for Claude Code
    └── bugs.md             # Security analysis
```

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| **Twitter 401 Error** | Check API keys, set permissions to "Read and Write" |
| **Gemini API Error** | Check API key and quota |
| **Trend Fetch Error** | Check if xtrends.iamrohit.in is accessible |
| **Database Locked** | Ensure only one bot instance is running |
| **WebSocket Not Connecting** | Ensure Flask app is running and port 5000 is open |

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository (`https://github.com/KilimcininKorOglu/AI-TwitterPersona/fork`)
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 🙏 Credits

- [Google Gemini AI](https://ai.google.dev) - AI tweet generation
- [Twitter API v2](https://developer.x.com) - Tweet posting
- [Flask](https://flask.palletsprojects.com) - Web dashboard
- [Socket.IO](https://socket.io) - Real-time communication

## ⚠️ Disclaimer

This tool is developed for educational purposes. Compliance with Twitter's terms of service is the user's responsibility. When using automated tweet posting:

- Follow Twitter's rate limits
- Don't produce spam content
- Don't share misleading or harmful content
- Respect platform rules

## 📞 Contact & Support

- **Issues**: [GitHub Issues](https://github.com/KilimcininKorOglu/AI-TwitterPersona/issues)
- **Discussions**: [GitHub Discussions](https://github.com/KilimcininKorOglu/AI-TwitterPersona/discussions)

---

**Developed with ❤️ using Claude AI**
