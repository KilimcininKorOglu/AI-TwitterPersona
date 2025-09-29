import time              # For sleep functionality and timing controls
import datetime as dt    # For current time checks and scheduling
import random           # For random topic selection from trending list
import os               # For environment variable access
import requests         # For HTTP requests (used in error handling)
from config import get_int_config, get_list_config, get_config  # Centralized configuration
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
TRENDS_LIMIT = get_int_config("TRENDS_LIMIT", 3)  # Number of trending topics to fetch (default: 3)
if TRENDS_LIMIT <= 0:
    TRENDS_LIMIT = 3
    print("[!] Warning: TRENDS_LIMIT must be positive, using default: 3")

SLEEP_HOURS = get_list_config("SLEEP_HOURS", ["1", "3", "9", "10"])
try:
    SLEEP_HOURS = [int(h.strip()) for h in SLEEP_HOURS]  # Hours when bot doesn't post
    # Validate all hours are in 0-23 range
    SLEEP_HOURS = [h for h in SLEEP_HOURS if 0 <= h <= 23]
    if not SLEEP_HOURS:
        SLEEP_HOURS = [1, 3, 9, 10]
        print("[!] Warning: Invalid SLEEP_HOURS values, using default: [1,3,9,10]")
except ValueError:
    SLEEP_HOURS = [1, 3, 9, 10]
    print("[!] Warning: Invalid SLEEP_HOURS format, using default: [1,3,9,10]")

NIGHT_MODE_START = get_int_config("NIGHT_MODE_START", 1)  # Start of night mode (inactive period)
if not 0 <= NIGHT_MODE_START <= 23:
    NIGHT_MODE_START = 1
    print("[!] Warning: NIGHT_MODE_START must be 0-23, using default: 1")
    print("[!] Warning: Invalid NIGHT_MODE_START value, using default: 1")

NIGHT_MODE_END = get_int_config("NIGHT_MODE_END", 6)      # End of night mode
if not 0 <= NIGHT_MODE_END <= 23:
    NIGHT_MODE_END = 6
    print("[!] Warning: NIGHT_MODE_END must be 0-23, using default: 6")

CYCLE_DURATION_MINUTES = get_int_config("CYCLE_DURATION_MINUTES", 60)  # Sleep time between tweet cycles
if CYCLE_DURATION_MINUTES <= 0:
    CYCLE_DURATION_MINUTES = 60
    print("[!] Warning: CYCLE_DURATION_MINUTES must be positive, using default: 60")

# Global variables for lazy initialization with thread safety
client = None
USER_ID = get_config("USER_ID")
_client_lock = threading.Lock()
_client_initialized = False

def initialize_twitter_client():
    """Initialize Twitter client with thread-safe error handling"""
    global client, _client_initialized
    
    # Quick check without lock for performance
    if _client_initialized:
        return True
    
    # Double-checked locking pattern for thread safety
    with _client_lock:
        if _client_initialized:
            return True  # Another thread already initialized
        
        if not initialize_bot_modules():
            return False
            
        try:
            print("[INFO] Initializing Twitter client (thread-safe)...")
            client = twitter_client.get_client()  # Get authenticated Twitter client
            if client is None:
                return False
            _client_initialized = True
            print("[+] Twitter client initialized successfully")
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
    import time
    STATUS = False  # Default status is failure
    max_retries = 3
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
                wait_time = (2 ** retry_count) * 60  # Exponential backoff: 2, 4, 8 minutes
                print(f"[!] Twitter API Rate Limit Exceeded. Waiting {wait_time//60} minutes before retry {retry_count}/{max_retries}")
                
                if retry_count < max_retries:
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

def getStatus():
    """
    Check if the bot should be active based on night mode settings.
    NOTE: This function is currently unused in the main bot loop.
    
    Returns:
        bool: True if bot should be active, False during night mode hours
    """
    hour = dt.datetime.now().hour
    # Return False during night mode hours (1-6 AM by default)
    if hour >= NIGHT_MODE_START and hour <= NIGHT_MODE_END:
        return False
    else:
        return True

def isTrendingTime():
    """
    Check if current time is appropriate for posting trending topic tweets.
    
    Returns:
        bool: True if bot should post trending tweets, False during sleep hours
    """
    hour = dt.datetime.now().hour
    # Don't post during configured sleep hours (1,3,9,10 by default)
    if hour in SLEEP_HOURS:
        return False
    return True

def trending_tweets():
    """
    Fetch trending topics and select one randomly for tweet generation.
    
    Returns:
        list or None: Selected trending topic as list, or None if error/no topics
    """
    limit = TRENDS_LIMIT  # Use configured limit for trending topics
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
    print(f"[+] Configuration: CYCLE_DURATION={CYCLE_DURATION_MINUTES} min, SLEEP_HOURS={SLEEP_HOURS}")

    # Initialize bot modules
    if not initialize_bot_modules():
        print("[!] Error: Could not initialize bot modules")
        logging.info("Please check your API configuration in token.env")
        return

    print("[+] Bot initialization complete. Entering main loop...")
    
    while True:
        prompt = ""  # Initialize prompt for AI tweet generation
        topic = ""   # Initialize topic container
        
        # Check if current time allows trending topic posting
        if isTrendingTime():
            print(f"[+] Getting Trending Topics...")
            
            # Fetch trending topics from Turkey
            topic = trending_tweets()
            if not topic:
                continue  # Skip this cycle if no trends found
            
            # Create detailed prompt for AI with trending topic information
            prompt += f"Bunlar tweet detayları. [format- konu, tweet sayısı, tweet URL] {topic}. Tüm bu detayları tweet bilgin için kullan, referans için değil."
            
            # Add context for better AI understanding
            context = " "  # Placeholder for user input (currently unused)
            if not context:
                context = "Kullanıcı tarafından ek bağlam eklenmedi. Konu detaylarını kullanarak bağlamı ve amacı anlamalısın. Tweet referansı için detayları kullan."
            prompt += context + " " + str(topic)
            
        else:
            # Use general prompt when not in trending time
            prompt = "En ilgi çekici ve güncel konuda bir tweet oluştur."
            
        # Generate AI-powered tweet using the prepared prompt
        print("Generating Reply...Topic: ", prompt)
        tweet = reply.generate_reply(prompt)

        # Check if tweet is None (political topic)
        if tweet is None:
            print("[!] Political topic detected, trying another trending topic...")
            # Skip this topic and try to get another one
            continue
        elif tweet:
            print(f"Tweet: {tweet}")

            # Auto-approve tweet posting (manual approval option commented out)
            option = "y"  # Automatic approval for autonomous operation
            
            if "y" == option:
                # Post the tweet to Twitter
                status = scheduled_tweet(tweet)
                
                # Log the tweet attempt to database (success or failure)
                database.save_tweets(tweet=tweet, tweet_type="tweet", status=status)
                
                # If tweet posting failed, continue to next cycle
                if not status:
                    continue
                
                # Successfully posted - begin sleep cycle
                print(f"[+] Bot Cycle Complete. Sleeping for {CYCLE_DURATION_MINUTES} minutes... ---\n")
                
                # Convert minutes to seconds for sleep timer
                timer = 60 * CYCLE_DURATION_MINUTES
                
                # Countdown timer with live display
                for i in range(timer + 1):
                    print(f"[+]Remaining Time [{timer-i}] ", end="\r")
                    time.sleep(1)  # Sleep for 1 second intervals
                    
            elif option == "n":
                continue  # Skip this cycle (unused in automatic mode)
            elif option == "exit":
                quit()    # Exit bot (unused in automatic mode)
                break
                
            print("\n")  # Add newline after cycle completion
        else:
            print("Reply not generated...")  # AI failed to generate tweet

# Start the bot when this module is executed directly
if __name__ == "__main__":
    run_bot()