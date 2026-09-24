import time              # For sleep functionality and timing controls
import datetime as dt    # For current time checks and scheduling
import random           # For random topic selection from trending list
import requests         # For HTTP requests (used in error handling)
from config import get_int_config, get_config, get_sleep_hours  # Centralized configuration
import logging  # For secure logging
import database       # SQLite database operations for tweet logging
import threading         # For thread-safe module initialization

# Lazy imports for API-dependent modules with thread safety
twitter_client = None
reply = None
trend = None

# Thread safety for module initialization
_init_lock = threading.Lock()
_modules_initialized = False

def initialize_bot_modules():
    """Initialize bot modules with thread-safe error handling"""
    global twitter_client, reply, trend, _modules_initialized
    
    # Quick check without lock for performance
    if _modules_initialized:
        return True
    
    # Double-checked locking pattern for thread safety
    with _init_lock:
        if _modules_initialized:
            return True  # Another thread already initialized
        
        try:
            print("[INFO] Initializing bot modules (thread-safe)...")
            import twitter_client as tc
            import reply as rp
            import trend as tr
            
            twitter_client = tc
            reply = rp
            trend = tr
            _modules_initialized = True
            print("[+] Bot modules initialized successfully")
            return True
        except Exception as e:
            error_msg = f"Could not initialize all bot modules: {type(e).__name__}: {str(e)}"
            logging.error(error_msg)
            logging.info("Bot initialization failed - check API credentials and configuration")
            logging.info("Required: Twitter API credentials and Gemini API key in token.env")
            return False

# Configuration loaded via centralized config module

# Bot Configuration - All values are customizable via environment variables with validation
# Settings are read on every use so changes saved from the dashboard reach a running bot
def get_trends_limit():
    """Number of trending topics to fetch (default: 3)."""
    limit = get_int_config("TRENDS_LIMIT", 3)
    if limit <= 0:
        print("[!] Warning: TRENDS_LIMIT must be positive, using default: 3")
        return 3
    return limit

def get_cycle_duration_minutes(default=60):
    """Sleep time between tweet cycles in minutes."""
    minutes = get_int_config("CYCLE_DURATION_MINUTES", default)
    if minutes <= 0:
        print(f"[!] Warning: CYCLE_DURATION_MINUTES must be positive, using default: {default}")
        return default
    return minutes

# Delays before retrying after a failed cycle, matching the dashboard bot thread
RETRY_DELAY_SECONDS = 60
POLITICAL_SKIP_DELAY_SECONDS = 10

# Global variables for lazy initialization with thread safety
client = None
USER_ID = get_config("USER_ID")
_client_lock = threading.Lock()
_client_initialized = False

def initialize_twitter_client():
    """Initialize Twitter client with thread-safe error handling"""
    global client, _client_initialized

    with _client_lock:
        if not initialize_bot_modules():
            return False

        try:
            # get_client() returns its cached client unless the credentials changed,
            # so updated keys from the dashboard take effect without a restart
            new_client = twitter_client.get_client()
            if new_client is None:
                client = None
                _client_initialized = False
                return False
            if new_client is not client:
                print("[+] Twitter client initialized successfully")
            client = new_client
            _client_initialized = True
            return True
        except Exception as e:
            logging.error(f"Error initializing Twitter client: {e}")
            logging.info("Please check your Twitter API credentials in token.env")
            return False

def get_initialization_status():
    """Get current initialization status for monitoring"""
    return {
        'modules_initialized': _modules_initialized,
        'client_initialized': _client_initialized,
        'client_available': client is not None
    }

def reset_initialization():
    """Reset initialization state (for testing purposes)"""
    global _modules_initialized, _client_initialized, client
    with _init_lock:
        with _client_lock:
            _modules_initialized = False
            _client_initialized = False
            client = None
            print("[INFO] Initialization state reset")


def scheduled_tweet(tweets):
    """
    Post a tweet to Twitter using the configured client.
    
    Args:
        tweets (str): The tweet content to be posted
        
    Returns:
        bool: True if tweet was posted successfully, False otherwise
    """
    STATUS = False  # Default status is failure
    max_retries = 3  # Total attempts, so at most two backoff waits
    retry_count = 0
    
    # Initialize Twitter client if needed
    if not initialize_twitter_client():
        print("[!] Cannot post tweet: Twitter client not initialized")
        return False
    
    while retry_count < max_retries:
        try:
            # Use Twitter API client to post the tweet
            client.create_tweet(text=tweets)
            print("[+] Scheduled Tweet sent.")
            STATUS = True  # Mark as successful
            return STATUS
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check for rate limit errors
            if "rate limit" in error_msg or "too many requests" in error_msg or "429" in error_msg:
                retry_count += 1
                wait_time = (2 ** retry_count) * 60  # Exponential backoff: 2, then 4 minutes

                if retry_count < max_retries:
                    print(f"[!] Twitter API Rate Limit Exceeded. Waiting {wait_time//60} minutes before attempt {retry_count + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                else:
                    print("[!] Max retries reached for rate limit. Tweet failed.")
                    break
            else:
                # Other errors (authentication, network, etc.)
                print(f"[!] Scheduled Tweet Error: {e}")
                break
                
    return STATUS

def isTrendingTime():
    """
    Check if current time is appropriate for posting trending topic tweets.
    
    Returns:
        bool: True if bot should post trending tweets, False during sleep hours
    """
    hour = dt.datetime.now().hour
    # Don't post during configured sleep hours (1,3,9,10 by default)
    if hour in get_sleep_hours():
        return False
    return True

def trending_tweets():
    """
    Fetch trending topics and select one randomly for tweet generation.
    
    Returns:
        list or None: Selected trending topic as list, or None if error/no topics
    """
    limit = get_trends_limit()  # Use configured limit for trending topics
    try:
        # Fetch trending topics from Turkey using trend module
        trend_tweet = trend.prepareTrend(limit=limit)
        if not trend_tweet:
            print("[!] No trending topics found")
            return None
        
        # Display all fetched trending topics for logging/debugging
        for t in trend_tweet:
            print(t)
            
        # Randomly select one topic from the list for variety
        return random.choices(trend_tweet)
    except requests.RequestException as e:
        # Handle network-related errors (timeout, connection issues, etc.)
        print(f"[!] Network error while fetching trends: {e}")
        return None
    except Exception as e:
        # Handle any other unexpected errors
        print(f"[!] Error fetching trending topics: {e}")
        return None
def run_bot():
    """
    Main bot execution loop - handles the complete tweet generation and posting cycle.

    This function runs indefinitely and performs the following steps:
    1. Check if it's appropriate time to post trending topics
    2. Fetch trending topics or use general prompt
    3. Generate AI-powered tweet using Gemini
    4. Post tweet to Twitter and log to database
    5. Sleep for configured duration before next cycle
    """
    print(f"[+] Bot starting at {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[+] Configuration: CYCLE_DURATION={get_cycle_duration_minutes()} min, SLEEP_HOURS={get_sleep_hours()}")

    # Create or migrate the database schema before the first save
    database.createDatabase()

    # Initialize bot modules
    if not initialize_bot_modules():
        print("[!] Error: Could not initialize bot modules")
        logging.info("Please check your API configuration in token.env")
        return

    print("[+] Bot initialization complete. Entering main loop...")

    while True:
        run_bot_cycle()

def build_prompt():
    """
    Build the AI prompt for one cycle.

    Returns:
        str or None: The prompt, or None when no trending topic was found
    """
    # Use general prompt when not in trending time
    if not isTrendingTime():
        return "En ilgi çekici ve güncel konuda bir tweet oluştur."

    print("[+] Getting Trending Topics...")
    topic = trending_tweets()
    if not topic:
        return None

    # Create detailed prompt for AI with trending topic information
    prompt = f"Bunlar tweet detayları. [format- konu, tweet sayısı, tweet URL] {topic}. Tüm bu detayları tweet bilgin için kullan, referans için değil."
    # Add context for better AI understanding
    context = "Kullanıcı tarafından ek bağlam eklenmedi. Konu detaylarını kullanarak bağlamı ve amacı anlamalısın. Tweet referansı için detayları kullan."
    return prompt + " " + context

def sleep_with_countdown(seconds):
    """Sleep for seconds while showing a live countdown."""
    for i in range(seconds + 1):
        print(f"[+]Remaining Time [{seconds-i}] ", end="\r")
        time.sleep(1)  # Sleep for 1 second intervals
    print("\n")  # Add newline after cycle completion

def run_bot_cycle():
    """Run one cycle: build a prompt, generate a tweet, post it and wait."""
    prompt = build_prompt()
    if prompt is None:
        time.sleep(RETRY_DELAY_SECONDS)  # Skip this cycle if no trends found
        return

    # Generate AI-powered tweet using the prepared prompt
    print("Generating Reply...Topic: ", prompt)
    tweet, persona = reply.generate_reply_with_persona(prompt)

    if tweet is None:
        # Political topic: skip it and try another one after a short wait
        print("[!] Political topic detected, trying another trending topic...")
        time.sleep(POLITICAL_SKIP_DELAY_SECONDS)
        return
    if not tweet:
        print("Reply not generated...")  # AI failed to generate tweet
        time.sleep(RETRY_DELAY_SECONDS)
        return

    print(f"Tweet: {tweet}")
    # Post the tweet and log the attempt to the database (success or failure)
    status = scheduled_tweet(tweet)
    database.save_tweets(tweet=tweet, tweet_type="tweet", status=status, persona=persona)
    if not status:
        time.sleep(RETRY_DELAY_SECONDS)
        return

    # Successfully posted - begin sleep cycle
    cycle_minutes = get_cycle_duration_minutes()
    print(f"[+] Bot Cycle Complete. Sleeping for {cycle_minutes} minutes... ---\n")
    sleep_with_countdown(60 * cycle_minutes)

# Start the bot when this module is executed directly
if __name__ == "__main__":
    run_bot()