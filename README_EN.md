# 🤖 AI-TwitterPersona

An automated Twitter bot that tracks real-time trending topics in Turkey and generates personalized tweets using Google Gemini AI.

## 🚀 Features

- **📈 Live Trend Monitoring**: Automatically fetches current trending topics from Turkey
- **🤖 AI Tweet Generation**: Creates tweets in your custom personality using Google Gemini 2.5 Flash
- **🎭 Smart Persona System**: 3 different writing styles (tech, casual, sad)
- **⏰ Scheduled Posting**: Hourly cycles, posts during optimal engagement hours
- **🛡️ Duplicate Prevention**: Topic classification cache and SQLite database
- **🌐 Web Dashboard**: Real-time bot control and monitoring
- **🔒 Security**: 25/25 security vulnerabilities fixed, production-ready

## 📋 Requirements

- **Python 3.8+**
- **Twitter Developer Account** - [developer.twitter.com](https://developer.twitter.com)
- **Google Gemini API Key** - [ai.google.dev](https://ai.google.dev)

## 🛠️ Installation

### Windows (Recommended)

```batch
# Automated setup (virtual environment + dependencies + database)
setup.bat

# Run CLI bot
start_bot.bat

# Web dashboard (development)
start_dashboard.bat

# Production server
start_production.bat
```

### Manual Installation

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate.bat
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Database setup
python database.py
```

## ⚙️ Configuration

Edit the `token.env` file with your API keys:

```env
# Twitter API (get from developer.twitter.com)
api_key=YOUR_TWITTER_API_KEY
api_secret=YOUR_TWITTER_API_SECRET
access_token=YOUR_ACCESS_TOKEN
access_token_secret=YOUR_ACCESS_TOKEN_SECRET
bearer_token=YOUR_BEARER_TOKEN
USER_ID=YOUR_TWITTER_USER_ID

# Google Gemini AI (get from ai.google.dev)
gemini_api_key=YOUR_GEMINI_API_KEY

# Bot Settings (optional)
TRENDS_LIMIT=3
SLEEP_HOURS=1,3,9,10
CYCLE_DURATION_MINUTES=60
GEMINI_MODEL=gemini-2.5-flash
AI_TEMPERATURE=0.85
```

## 🚀 Usage

### CLI Bot

```bash
python main.py
```

The bot automatically:
1. ⏰ Checks time (skips posting during hours 1,3,9,10)
2. 📈 Fetches top 3 trending topics from Turkey
3. 🎯 Classifies topic (tech/casual/sad)
4. ✍️ Generates 285-character tweet with appropriate persona
5. 🐦 Posts to Twitter and saves to SQLite
6. 💤 Waits 1 hour and repeats

### Web Dashboard

```bash
python app.py
```

Dashboard features:
- 📊 Real-time bot status
- 🎛️ Start/stop bot control
- 📝 Manual tweet posting
- 📈 Analytics and statistics
- ⚙️ Live configuration editor

## 🎭 Persona System

Your custom personality with 3 different writing styles:

- **Tech** 💻: Confident, witty technology commentary
- **Casual** 😊: Istanbul-style, friendly, movie references
- **Sad** 😢: Empathetic, understanding, respectful tone

## 📊 Example Output

```
[+] Getting Trending Topics...
1. #AIRevolution (45K Tweets) URL: https://twitter.com/search?q=%23AIRevolution
2. #TechTrends (23K Tweets) URL: https://twitter.com/search?q=%23TechTrends
3. #Innovation (18K Tweets) URL: https://twitter.com/search?q=%23Innovation

Generating Tweet... Topic: #AIRevolution (45K Tweets)
Tweet: The AI wave isn't coming—it's already here. Adapt or get left behind. 🚀 #AIRevolution
✅ Tweet sent successfully.
[+] Tweet saved to database.
[+] Bot cycle completed. Waiting 1 hour...
```

## 🔒 Security

✅ **Production Ready** - 25/25 security vulnerabilities fixed:

- **Thread Safety**: Proper locking for database operations
- **Input Validation**: Comprehensive config validation and sanitization
- **CSRF Protection**: Secure token handling via API endpoints
- **SQL Injection**: Parameterized queries and table name validation
- **Rate Limiting**: Dynamic backoff with exponential retry logic
- **Memory Management**: LRU caches and resource leak prevention

## 📁 Project Structure

```bash
AI-TwitterPersona/
├── 🤖 Core Bot
│   ├── main.py              # Main bot loop
│   ├── reply.py             # AI tweet generation
│   ├── trend.py             # Trend scraping
│   ├── database.py          # SQLite operations
│   ├── twitter_client.py    # Twitter API
│   └── config.py            # Centralized configuration
├── 🌐 Web Dashboard  
│   ├── app.py               # Flask web application
│   ├── production.py        # Production WSGI
│   └── templates/           # HTML templates
├── ⚙️ Configuration
│   ├── requirements.txt     # Python dependencies
│   ├── token.env           # API keys
│   └── gunicorn.conf.py    # Server settings
└── 🚀 Windows Scripts
    ├── setup.bat           # Automated setup
    ├── start_bot.bat       # Start bot
    └── start_dashboard.bat # Start dashboard
```

## 🧪 Test Commands

```bash
# Database test
python -c "import database; database.createDatabase()"

# Trend fetching test
python -c "import trend; trends = trend.prepareTrend(3); print(f'{len(trends)} trends found' if trends else 'No trends found')"

# AI tweet generation test
python -c "import reply; print(reply.generate_reply('artificial intelligence'))"

# Twitter client test
python -c "import twitter_client; client = twitter_client.get_client(); print('Twitter client ready')"
```

## 📝 License

This project is developed for **educational purposes**. Use responsibly and comply with Twitter's terms of service.

## 🤝 Contributing

1. Fork this repository
2. Create feature branch (`git checkout -b new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin new-feature`)
5. Create Pull Request

## ❓ Support

For issues and suggestions, use the [Issues](https://github.com/KilimcininKorOglu/AI-TwitterPersona/issues) tab.

---

**⚠️ Disclaimer**: This tool automates Twitter posts. Users are responsible for compliance with Twitter's terms of service and applicable laws.

**🎯 Target Audience**: Designed for personal branding, marketing, and technology creators.