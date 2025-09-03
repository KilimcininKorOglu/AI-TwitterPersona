from config import get_config, get_float_config, get_int_config  # Centralized configuration
import os                          # For environment variable access
import logging  # For secure logging
import json                        # For cache file operations
import google.generativeai as genai    # Google Gemini AI API
import google.api_core.exceptions      # For specific Gemini API error handling
import database                    # For database operations (avoid runtime import)

# Configuration loaded via centralized config module

# Safe configuration parsing with error handling and validation
def safe_float_config(key, default_value, min_val=None, max_val=None):
    """Safely parse float configuration with validation and error handling"""
    try:
        value = get_float_config(key, default_value)
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

# AI Model Configuration - all parameters customizable via environment variables with safe parsing
GEMINI_MODEL = get_config("GEMINI_MODEL", "gemini-2.5-flash")          # AI model version
AI_TEMPERATURE = safe_float_config("AI_TEMPERATURE", 0.85, 0.0, 2.0)  # Creativity level (0.0-2.0)
AI_TOP_P = safe_float_config("AI_TOP_P", 0.9, 0.0, 1.0)              # Nucleus sampling parameter (0.0-1.0)
AI_TOP_K = safe_int_config("AI_TOP_K", 40, 1, 100)                    # Top-k sampling parameter (1-100)

# Startup configuration validation
def validate_startup_config():
    """Validate all configuration values at startup"""
    issues = []
    
    # Check model name
    if not GEMINI_MODEL or not isinstance(GEMINI_MODEL, str):
        issues.append(f"GEMINI_MODEL invalid: '{GEMINI_MODEL}'")
    
    # Validate temperature range
    if not 0.0 <= AI_TEMPERATURE <= 2.0:
        issues.append(f"AI_TEMPERATURE out of range: {AI_TEMPERATURE} (should be 0.0-2.0)")
    
    # Validate top_p range
    if not 0.0 <= AI_TOP_P <= 1.0:
        issues.append(f"AI_TOP_P out of range: {AI_TOP_P} (should be 0.0-1.0)")
    
    # Validate top_k range
    if not 1 <= AI_TOP_K <= 100:
        issues.append(f"AI_TOP_K out of range: {AI_TOP_K} (should be 1-100)")
    
    if issues:
        print("[ERROR] Configuration validation failed:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print(f"[+] Configuration validated: Model={GEMINI_MODEL}, Temperature={AI_TEMPERATURE}, TopP={AI_TOP_P}, TopK={AI_TOP_K}")
        return True

# Run startup validation
validate_startup_config()

# Global variables for lazy initialization
model = None
gemini_api_key = None

def initialize_gemini():
    """Initialize Gemini AI with API key validation"""
    global model, gemini_api_key
    
    if model is not None:
        return True  # Already initialized
    
    # Validate Gemini API key
    gemini_api_key = get_config("gemini_api_key")
    if not gemini_api_key or gemini_api_key == "YOUR_GEMINI_API_KEY":
        logging.warning("Gemini API key not found or not configured")
        logging.info("Please get your API key from https://ai.google.dev/ and update token.env")
        return False
    
    try:
        # Configure Gemini AI with validated API key
        genai.configure(api_key=gemini_api_key)
        
        # Initialize the Gemini AI model with configured settings
        model = genai.GenerativeModel(GEMINI_MODEL)
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
    
    Args:
        user_input (str): The topic/prompt to be classified
        
    Returns:
        str: One of 'tech', 'casual', or 'sad' - defaults to 'casual' on any error
    """
    # Normalize input for consistent cache lookup
    normalized = user_input.strip().lower()
    
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
        prompt = f"""Aşağıdaki tweet konusunu şu kategorilerden birine sınıflandır: tech, casual, or sad.
Tweet: "{user_input}"
Sadece kategori adını döndür."""
        
        # Get classification from Gemini AI
        resp = model.generate_content(prompt)
        category = resp.text.strip().lower()
        
        # Validate response and default to 'casual' if invalid
        if category not in ["tech", "casual", "sad"]:
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

    # Cache the result for future use with timestamp
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
    
    Args:
        user_input (str): The topic or trending subject to generate a tweet about
        
    Returns:
        str: Generated tweet text (max 285 characters) or empty string on error
    """
    # Initialize Gemini if not already done
    if not initialize_gemini():
        print("[!] Cannot generate reply: Gemini API not initialized")
        return ""
    
    # Classify the topic to determine appropriate persona
    topic = detect_topic_type(user_input)
    
    # Get the corresponding persona prompt from database
    active_prompts = database.get_active_prompts_dict()
    
    # Use database prompts only - if database fails, don't generate tweet
    if not active_prompts or topic not in active_prompts:
        print(f"[!] Error: No prompt found for '{topic}' persona in database")
        print(f"[!] Please configure prompts via web interface at /prompts")
        return ""  # Return empty string to indicate failure
    
    persona = active_prompts[topic]
    print(f"[+] Using database prompt for '{topic}' persona")
    
    # Start a new conversation with Gemini AI
    convo = model.start_chat(history=[])
    
    # Generate tweet using persona prompt and topic, with configured AI parameters
    try:
        resp = convo.send_message(
            persona + "\nTopic: " + user_input,
            generation_config={
                "temperature": AI_TEMPERATURE,     # Controls creativity/randomness
                "top_p": AI_TOP_P,                # Nucleus sampling parameter
                "top_k": AI_TOP_K,                # Top-k sampling parameter  
                "max_output_tokens": None         # No limit on response length
            }
        )
        
        # Return cleaned response text
        return resp.text.strip()
        
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
        import time
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
