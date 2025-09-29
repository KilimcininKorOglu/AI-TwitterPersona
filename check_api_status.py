"""
Check real-time API connection status
"""

import time
import os
from dotenv import load_dotenv
import tweepy
import google.generativeai as genai
import requests
from config import get_config

# Load environment variables
load_dotenv("token.env")

def check_twitter_api():
    """Check Twitter API connection status"""
    try:
        start = time.time()

        # Get credentials
        api_key = get_config("api_key")
        api_secret = get_config("api_secret")
        access_token = get_config("access_token")
        access_token_secret = get_config("access_token_secret")

        if not all([api_key, api_secret, access_token, access_token_secret]):
            return {"status": "error", "message": "Missing credentials", "ping": None}

        # Test connection
        auth = tweepy.OAuthHandler(api_key, api_secret)
        auth.set_access_token(access_token, access_token_secret)
        api = tweepy.API(auth)

        # Verify credentials
        api.verify_credentials()

        ping = int((time.time() - start) * 1000)  # Convert to ms
        return {"status": "success", "message": "Connected", "ping": ping}

    except tweepy.TweepyException as e:
        return {"status": "error", "message": str(e), "ping": None}
    except Exception as e:
        return {"status": "error", "message": str(e), "ping": None}

def check_gemini_api():
    """Check Gemini AI API connection status"""
    try:
        start = time.time()

        # Get API key
        gemini_api_key = get_config("gemini_api_key")

        if not gemini_api_key:
            return {"status": "error", "message": "Missing API key", "ping": None}

        # Configure Gemini
        genai.configure(api_key=gemini_api_key)

        # Test with a simple prompt
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content("Test")

        if response:
            ping = int((time.time() - start) * 1000)  # Convert to ms
            return {"status": "success", "message": "Connected", "ping": ping}
        else:
            return {"status": "error", "message": "No response", "ping": None}

    except Exception as e:
        return {"status": "error", "message": str(e), "ping": None}

def check_trends_api():
    """Check Trends API connection status"""
    try:
        start = time.time()

        # Get trends URL
        trends_url = get_config("TRENDS_URL", "https://xtrends.iamrohit.in/turkey")

        # Test connection
        response = requests.get(trends_url, timeout=5)

        if response.status_code == 200:
            ping = int((time.time() - start) * 1000)  # Convert to ms
            return {"status": "success", "message": "Connected", "ping": ping}
        else:
            return {"status": "warning", "message": f"Status {response.status_code}", "ping": None}

    except requests.RequestException as e:
        return {"status": "error", "message": str(e), "ping": None}
    except Exception as e:
        return {"status": "error", "message": str(e), "ping": None}

def check_database():
    """Check database connection status"""
    try:
        import sqlite3
        from config import get_config

        start = time.time()

        db_name = get_config("DB_NAME", "twitter.db")
        conn = sqlite3.connect(db_name)

        # Test query
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tweets")
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        ping = int((time.time() - start) * 1000)  # Convert to ms
        return {"status": "success", "message": f"Connected ({result[0]} tweets)", "ping": ping}

    except Exception as e:
        return {"status": "error", "message": str(e), "ping": None}

def get_all_api_status():
    """Get status of all APIs"""
    return {
        "twitter": check_twitter_api(),
        "gemini": check_gemini_api(),
        "trends": check_trends_api(),
        "database": check_database()
    }

if __name__ == "__main__":
    print("[API Status Check]")
    print("=" * 50)

    status = get_all_api_status()

    for api_name, api_status in status.items():
        status_icon = "✅" if api_status["status"] == "success" else "⚠️" if api_status["status"] == "warning" else "❌"
        ping_str = f"{api_status['ping']}ms" if api_status['ping'] else "N/A"
        print(f"{status_icon} {api_name.upper()}: {api_status['message']} (Ping: {ping_str})")