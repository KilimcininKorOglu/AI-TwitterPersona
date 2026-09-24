from config import get_config, get_float_config, get_int_config  # Centralized configuration
import os                          # For environment variable access
import logging  # For secure logging
import json                        # For cache file operations
import math                        # For finite float checks
import time                        # For quota backoff sleeps
import requests                    # For network exception types
import google.generativeai as genai    # Google Gemini AI API
import google.api_core.exceptions      # For specific Gemini API error handling
import database                    # For database operations (avoid runtime import)
from tweet_length import fits_in_tweet, tweet_length, TWEET_MAX_LENGTH

# Configuration loaded via centralized config module

# Safe configuration parsing with error handling and validation
def safe_float_config(key, default_value, min_val=None, max_val=None):
    """Safely parse float configuration with validation and error handling"""
    try:
        value = get_float_config(key, default_value)
        if not math.isfinite(value):
            print(f"[WARNING] {key}={value} is not a finite number, using default {default_value}")
            return default_value
        if min_val is not None and value < min_val:
            print(f"[WARNING] {key}={value} is below minimum {min_val}, using {min_val}")
            return min_val
        if max_val is not None and value > max_val:
            print(f"[WARNING] {key}={value} is above maximum {max_val}, using {max_val}")
            return max_val
        return value
    except (ValueError, TypeError) as e:
        print(f"[ERROR] Invalid {key} value '{os.getenv(key)}': {e}. Using default: {default_value}")
        return default_value

def safe_int_config(key, default_value, min_val=None, max_val=None):
    """Safely parse integer configuration with validation and error handling"""
    try:
        value = get_int_config(key, default_value)
        if min_val is not None and value < min_val:
            print(f"[WARNING] {key}={value} is below minimum {min_val}, using {min_val}")
            return min_val
        if max_val is not None and value > max_val:
            print(f"[WARNING] {key}={value} is above maximum {max_val}, using {max_val}")
            return max_val
        return value
    except (ValueError, TypeError) as e:
        print(f"[ERROR] Invalid {key} value: {e}. Using default: {default_value}")
        return default_value

# AI Model Configuration - read on every use so settings saved from the dashboard
# reach a running bot without a restart
def get_ai_settings():
    """Return the current Gemini model name and sampling parameters."""
    return {
        "model": get_config("GEMINI_MODEL", "gemini-2.5-flash"),          # AI model version
        "temperature": safe_float_config("AI_TEMPERATURE", 0.85, 0.0, 2.0),  # Creativity level (0.0-2.0)
        "top_p": safe_float_config("AI_TOP_P", 0.9, 0.0, 1.0),              # Nucleus sampling parameter (0.0-1.0)
        "top_k": safe_int_config("AI_TOP_K", 40, 1, 100),                    # Top-k sampling parameter (1-100)
    }

# Startup configuration validation
def validate_startup_config():
    """Validate all configuration values at startup"""
    issues = []
    settings = get_ai_settings()

    # Check model name
    if not settings["model"] or not isinstance(settings["model"], str):
        issues.append(f"GEMINI_MODEL invalid: '{settings['model']}'")

    if issues:
        print("[ERROR] Configuration validation failed:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print(f"[+] Configuration validated: Model={settings['model']}, Temperature={settings['temperature']}, TopP={settings['top_p']}, TopK={settings['top_k']}")
        return True

# Run startup validation
validate_startup_config()

class QuotaBackoff:
    """Track consecutive Gemini quota failures to scale the backoff delay."""

    def __init__(self):
        self.consecutive_failures = 0

    def record_failure(self):
        self.consecutive_failures += 1

    def record_success(self):
        self.consecutive_failures = 0

rate_limiter = QuotaBackoff()

# Global variables for lazy initialization
model = None
_model_key = None  # (api key, model name) the cached model was built with

def initialize_gemini():
    """Initialize Gemini AI with API key validation; rebuild when the key or model changes"""
    global model, _model_key

    # Validate Gemini API key
    gemini_api_key = get_config("gemini_api_key")
    if not gemini_api_key or gemini_api_key == "YOUR_GEMINI_API_KEY":
        logging.warning("Gemini API key not found or not configured")
        logging.info("Please get your API key from https://ai.google.dev/ and update token.env")
        return False

    model_name = get_ai_settings()["model"]
    if model is not None and _model_key == (gemini_api_key, model_name):
        return True  # Already initialized with the current settings

    try:
        # Configure Gemini AI with validated API key
        genai.configure(api_key=gemini_api_key)

        # Initialize the Gemini AI model with configured settings
        model = genai.GenerativeModel(model_name)
        _model_key = (gemini_api_key, model_name)
        return True
    except Exception as e:
        print(f"[!] Error initializing Gemini: {e}")
        return False

# Cache Configuration for topic classification optimization
CACHE_FILENAME = "topic_cache.json"  # File to store topic classification results

# Load existing topic classification cache to avoid re-processing same topics
if os.path.exists(CACHE_FILENAME):
    try:
        with open(CACHE_FILENAME, 'r', encoding='utf-8') as f:
            topic_cache = json.load(f)
        print(f"[+] Topic cache loaded from {CACHE_FILENAME} ({len(topic_cache)} entries)")
    except Exception as e:
        print(f"[!] Error loading cache: {e}")
        topic_cache = {}  # Initialize empty cache on error
else:
    topic_cache = {}  # Initialize empty cache if file doesn't exist
    print(f"[INFO] No existing cache file found, starting with empty cache")

# Dynamic AI Persona System - All prompts are stored in database
# This allows web-based editing and complete customization of persona


def detect_topic_type(user_input):
    """
    Classify the input topic into one of three persona categories: tech, casual, or sad.
    Uses caching to avoid re-classifying the same topics and improve performance.
    Returns 'political' for political content to skip.

    Args:
        user_input (str): The topic/prompt to be classified

    Returns:
        str: One of 'tech', 'casual', 'sad', or 'political' - defaults to 'casual' on any error
    """
    # Extract hashtag from complex prompt if present
    import re
    hashtag_pattern = r'#[\w\u00C0-\u024F\u1E00-\u1EFF]+'
    hashtag_match = re.search(hashtag_pattern, user_input)

    if hashtag_match:
        # Use only the hashtag for classification
        topic_to_classify = hashtag_match.group(0)
        print(f"[+] Extracted hashtag for classification: {topic_to_classify}")
    else:
        # Use the original input if no hashtag found
        topic_to_classify = user_input

    # Normalize input for consistent cache lookup
    normalized = topic_to_classify.strip().lower()
    
    # Check cache first to avoid unnecessary API calls
    if normalized in topic_cache:
        cached_data = topic_cache[normalized]
        # Handle both old string format and new dict format with timestamp
        if isinstance(cached_data, str):
            print(f"[+] Using cached classification (legacy): {user_input} -> {cached_data}")
            return cached_data
        elif isinstance(cached_data, dict) and 'category' in cached_data:
            # Check if cache entry is still valid (less than 7 days old)
            if 'timestamp' in cached_data:
                from datetime import datetime, timedelta
                try:
                    entry_time = datetime.fromisoformat(cached_data['timestamp'])
                    if datetime.now() - entry_time >= timedelta(days=7):
                        print(f"[INFO] Cache entry expired for: {user_input}, re-classifying")
                        del topic_cache[normalized]
                    else:
                        print(f"[+] Using cached classification: {user_input} -> {cached_data['category']}")
                        return cached_data['category']
                except:
                    # If timestamp parsing fails, use cached value anyway
                    print(f"[+] Using cached classification (timestamp error): {user_input} -> {cached_data['category']}")
                    return cached_data['category']
            else:
                print(f"[+] Using cached classification (no timestamp): {user_input} -> {cached_data['category']}")
                return cached_data['category']
        else:
            # Fallback for unknown format
            category_fallback = str(cached_data)
            print(f"[+] Using cached classification (fallback): {user_input} -> {category_fallback}")
            return category_fallback

    # Initialize Gemini if not already done
    if not initialize_gemini():
        print("[!] Cannot classify topic: Gemini API not initialized")
        return "casual"  # Default fallback

    try:
        # Create classification prompt for Gemini AI
        prompt = f"""Aşağıdaki hashtag veya konuyu analiz et ve şu kategorilerden birine sınıflandır:
- political: SİYASET, parti, siyasetçi, seçim, hükümet, muhalefet, meclis, vekil, bakan, cumhurbaşkanı ile ilgili konular
- tech: Teknoloji, bilim, yazılım, startup, kripto, AI konuları
- sad: Üzücü haberler, ölüm, hastalık, felaket, kayıplar
- casual: Diğer tüm konular (günlük hayat, spor, magazin, eğlence, sosyal medya trendleri)

ÖNEMLİ: Eğer konu siyasi ise MUTLAKA "political" döndür.

Konu: "{topic_to_classify}"
Sadece kategori adını döndür (political/tech/sad/casual)."""
        
        # Get classification from Gemini AI
        resp = model.generate_content(prompt)
        category = resp.text.strip().lower()
        rate_limiter.record_success()
        
        # Validate response and default to 'casual' if invalid
        if category not in ["tech", "casual", "sad", "political"]:
            category = "casual"
            
    except google.api_core.exceptions.InvalidArgument as e:
        # Handle invalid API key or malformed request
        print(f"[!] Gemini API error (Invalid API key or request): {e}")
        category = "casual"
    except google.api_core.exceptions.ResourceExhausted as e:
        # Handle API quota exceeded errors with intelligent backoff
        rate_limiter.record_failure()
        print(f"[!] Gemini API quota exceeded: {e}")
        
        # Dynamic backoff based on failure count
        backoff_time = min(2 ** rate_limiter.consecutive_failures * 60, 1800)  # Max 30 minutes
        print(f"[!] Waiting {backoff_time//60} minutes for quota reset (failure #{rate_limiter.consecutive_failures})")
        
        time.sleep(backoff_time)
        category = "casual"
    except google.api_core.exceptions.PermissionDenied as e:
        # Handle permission denied errors
        logging.error(f"Gemini API permission denied: {str(e)}")
        category = "casual"
    except google.api_core.exceptions.NotFound as e:
        # Handle model not found errors
        logging.error(f"Gemini model not found: {str(e)}")
        category = "casual"
    except google.api_core.exceptions.DeadlineExceeded as e:
        # Handle timeout errors
        logging.error(f"Gemini API timeout: {str(e)}")
        category = "casual"
    except google.api_core.exceptions.ServiceUnavailable as e:
        # Handle service unavailable errors
        logging.error(f"Gemini service unavailable: {str(e)}")
        category = "casual"
    except requests.exceptions.ConnectionError as e:
        # Handle network connection errors
        logging.error(f"Network connection error: {str(e)}")
        category = "casual"
    except requests.exceptions.Timeout as e:
        # Handle request timeout errors
        logging.error(f"Request timeout error: {str(e)}")
        category = "casual"
    except json.JSONDecodeError as e:
        # Handle JSON parsing errors in API response
        logging.error(f"JSON decode error in API response: {str(e)}")
        category = "casual"
    except Exception as e:
        # Handle any other unexpected errors with full error details
        logging.error(f"Unexpected topic classification error: {type(e).__name__}: {str(e)}")
        category = "casual"
    else:
        # Cache only real classifications; an error fallback must not pin a
        # political topic to 'casual' for the whole cache lifetime
        from datetime import datetime
        topic_cache[normalized] = {
            'category': category,
            'timestamp': datetime.now().isoformat()
        }
        save_cache()  # Save cache to disk for persistence
    return category

def generate_reply(user_input):
    """
    Generate a tweet response using the appropriate persona based on topic classification.
    Skips political topics and returns None to indicate skipping.

    Args:
        user_input (str): The topic or trending subject to generate a tweet about

    Returns:
        str: Generated tweet text (max 280 characters), None for political topics, or empty string on error
    """
    return generate_reply_with_persona(user_input)[0]

def generate_reply_with_persona(user_input):
    """
    Generate a tweet like generate_reply and also return the persona it used.

    Args:
        user_input (str): The topic or trending subject to generate a tweet about

    Returns:
        tuple: (tweet text, None or empty string as in generate_reply; persona type or None)
    """
    # Initialize Gemini if not already done
    if not initialize_gemini():
        print("[!] Cannot generate reply: Gemini API not initialized")
        return "", None

    # Classify the topic to determine appropriate persona
    topic = detect_topic_type(user_input)

    # Skip political topics
    if topic == "political":
        print(f"[!] Political topic detected, skipping: {user_input[:50]}...")
        return None, topic  # None indicates the political topic should be skipped

    # Get the corresponding persona prompt from database
    active_prompts = database.get_active_prompts_dict()

    # Use database prompts only - if database fails, don't generate tweet
    if not active_prompts or topic not in active_prompts:
        print(f"[!] Error: No prompt found for '{topic}' persona in database")
        print(f"[!] Please configure prompts via web interface at /prompts")
        return "", topic  # Empty string indicates failure

    print(f"[+] Using database prompt for '{topic}' persona")
    return generate_text_for_persona(user_input, active_prompts[topic]), topic

def generate_text_for_persona(user_input, persona):
    """
    Generate tweet text with Gemini for one persona prompt.

    Args:
        user_input (str): The topic or trending subject to generate a tweet about
        persona (str): Formatted persona prompt

    Returns:
        str: Generated tweet text, or empty string on error or when it is too long
    """

    # Start a new conversation with Gemini AI
    convo = model.start_chat(history=[])
    
    # Extract hashtag if present for better context
    import re
    hashtag_pattern = r'#[\w\u00C0-\u024F\u1E00-\u1EFF]+'
    hashtag_match = re.search(hashtag_pattern, user_input)

    if hashtag_match:
        hashtag = hashtag_match.group(0)
        # Create context-aware prompt
        context_prompt = f"""{persona}

Şu an trending olan hashtag: {hashtag}
Bu hashtag hakkında, bu hashtag'i kullanarak bir tweet yaz.
Hashtag'in konusuna uygun, alakalı bir içerik üret.

Önemli:
- Hashtag'in konusuyla alakalı tweet yaz
- Eğer hashtag bir kişi ismiyse, o kişi hakkında yorum yap
- Eğer hashtag bir spor maçıysa, maç hakkında yorum yap
- Eğer hashtag bir olayla ilgiliyse, o olay hakkında yorum yap
- Maksimum 280 karakter, Türkçe

Hashtag: {hashtag}"""
    else:
        # Fallback to original format if no hashtag
        context_prompt = persona + "\nKonu: " + user_input

    # Generate tweet using persona prompt and topic, with configured AI parameters
    settings = get_ai_settings()
    try:
        resp = convo.send_message(
            context_prompt,
            generation_config={
                "temperature": settings["temperature"],  # Controls creativity/randomness
                "top_p": settings["top_p"],              # Nucleus sampling parameter
                "top_k": settings["top_k"],              # Top-k sampling parameter
                "max_output_tokens": None         # No limit on response length
            }
        )
        
        # Return cleaned response text
        text = resp.text.strip()
        rate_limiter.record_success()

        # Twitter rejects over-long tweets; skip so the caller retries with a new generation
        if not fits_in_tweet(text):
            print(f"[!] Generated tweet is {tweet_length(text)} characters (limit {TWEET_MAX_LENGTH}), skipping")
            return ""
        return text
        
    except google.api_core.exceptions.ResourceExhausted as e:
        # Handle API quota exceeded errors with dynamic backoff
        rate_limiter.record_failure()
        print(f"[!] Gemini API quota exceeded during tweet generation: {e}")
        
        # Dynamic backoff based on failure count
        backoff_time = min(2 ** rate_limiter.consecutive_failures * 300, 3600)  # Max 1 hour
        print(f"[!] Pausing bot for {backoff_time//60} minutes (failure #{rate_limiter.consecutive_failures})")
        
        time.sleep(backoff_time)
        return ""  # Return empty string to indicate failure
        
    except google.api_core.exceptions.InvalidArgument as e:
        # Handle invalid arguments or API key errors
        logging.error(f"Gemini API invalid argument error: {str(e)}")
        return ""
    except google.api_core.exceptions.PermissionDenied as e:
        # Handle permission denied errors
        logging.error(f"Gemini API permission denied: {str(e)}")
        return ""
    except google.api_core.exceptions.NotFound as e:
        # Handle model not found errors
        logging.error(f"Gemini model not found: {str(e)}")
        return ""
    except google.api_core.exceptions.DeadlineExceeded as e:
        # Handle timeout errors
        logging.error(f"Gemini API timeout during generation: {str(e)}")
        return ""
    except google.api_core.exceptions.ServiceUnavailable as e:
        # Handle service unavailable errors
        logging.error(f"Gemini service unavailable during generation: {str(e)}")
        return ""
    except google.api_core.exceptions.InternalServerError as e:
        # Handle internal server errors
        logging.error(f"Gemini internal server error: {str(e)}")
        return ""
    except requests.exceptions.ConnectionError as e:
        # Handle network connection errors
        logging.error(f"Network connection error during generation: {str(e)}")
        return ""
    except requests.exceptions.Timeout as e:
        # Handle request timeout errors
        logging.error(f"Request timeout during generation: {str(e)}")
        return ""
    except json.JSONDecodeError as e:
        # Handle JSON parsing errors in API response
        logging.error(f"JSON decode error in generation response: {str(e)}")
        return ""
    except Exception as e:
        # Handle any other unexpected errors with full error details
        logging.error(f"Unexpected tweet generation error: {type(e).__name__}: {str(e)}")
        return ""

def save_cache():
    """
    Save the topic classification cache to disk for persistence across bot restarts.
    This prevents re-classifying the same topics and improves performance.
    
    Includes automatic cache expiration for entries older than 7 days.
    """
    try:
        from datetime import datetime, timedelta

        # Clean expired entries (older than 7 days)
        current_time = datetime.now()
        cleaned_cache = {}
        
        for topic, data in topic_cache.items():
            # If data is just a string, convert to new format with timestamp
            if isinstance(data, str):
                cleaned_cache[topic] = {
                    'category': data,
                    'timestamp': current_time.isoformat()
                }
            elif isinstance(data, dict) and 'timestamp' in data:
                # Check if entry is less than 7 days old
                entry_time = datetime.fromisoformat(data['timestamp'])
                if current_time - entry_time < timedelta(days=7):
                    cleaned_cache[topic] = data
                else:
                    print(f"[INFO] Expired cache entry removed: {topic}")
            else:
                # Legacy format, keep with current timestamp
                cleaned_cache[topic] = {
                    'category': str(data),
                    'timestamp': current_time.isoformat()
                }
        
        # Update global cache with cleaned version
        topic_cache.clear()
        topic_cache.update(cleaned_cache)
        
        # Write cache to JSON file with pretty formatting
        with open(CACHE_FILENAME, 'w', encoding='utf-8') as f:
            json.dump(topic_cache, f, indent=4, ensure_ascii=False)
        print(f"[+] Topic cache saved to {CACHE_FILENAME} ({len(topic_cache)} entries)")
    except Exception as e:
        print(f"[!] Error saving cache: {e}")

# Main execution
if __name__ == "__main__":
    print("Reply generation module ready for use!")
