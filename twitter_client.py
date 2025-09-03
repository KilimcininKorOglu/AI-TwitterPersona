import os                    # For environment variable access
import tweepy               # Twitter API library for Python
from config import get_config  # Centralized configuration
import logging  # For secure logging

# Extract Twitter API credentials from environment variables
api_key = get_config("api_key")                        # Consumer Key (API Key)
api_secret = get_config("api_secret")                  # Consumer Secret (API Secret Key)
access_token = get_config("access_token")              # Access Token
access_token_secret = get_config("access_token_secret") # Access Token Secret
bearer_token = get_config("bearer_token")              # Bearer Token (for API v2)
USER_ID = get_config("USER_ID")                        # Twitter User ID (numeric)

# Credential Validation - check for missing or placeholder values
required_credentials = {
    "api_key": api_key,
    "api_secret": api_secret, 
    "access_token": access_token,
    "access_token_secret": access_token_secret,
    "bearer_token": bearer_token
}

# Identify missing credentials or placeholder values (starting with "YOUR_")
missing_credentials = [key for key, value in required_credentials.items() 
                      if not value or value.startswith("YOUR_")]

# Global client variable for lazy initialization
client = None

def validate_credentials():
    """Validate Twitter API credentials with standardized error messages"""
    global missing_credentials
    if missing_credentials:
        error_msg = f"Missing Twitter API credentials: {', '.join(missing_credentials)}"
        logging.error(error_msg)
        logging.info("Required credentials: api_key, api_secret, access_token, access_token_secret, bearer_token")
        logging.info("Get your credentials from: https://developer.twitter.com/en/portal/dashboard")
        logging.info("Update them in token.env file")
        return False
    
    # Validate credential format
    if api_key and len(api_key) < 10:
        logging.error("API key appears to be invalid (too short)")
        return False
    if bearer_token and not bearer_token.startswith('AAAA'):
        logging.error("Bearer token appears to be invalid (wrong format)")
        return False
        
    return True

def get_client():
    """
    Create and return a configured Twitter API client using Tweepy.
    
    This function initializes a Tweepy Client with all required authentication
    credentials for both Twitter API v1.1 and v2 endpoints.
    
    Returns:
        tweepy.Client: Authenticated Twitter client ready for API calls or None if credentials missing
        
    Raises:
        Exception: If client creation fails (re-raised for proper error handling)
        
    Note:
        This function validates credentials before creating the client.
        credentials are present in the environment variables.
    """
    global client
    
    if client is not None:
        return client  # Already initialized
    
    # Validate credentials first
    if not validate_credentials():
        return None
        
    try:
        # Initialize Tweepy client with all authentication methods
        client = tweepy.Client(
            consumer_key=api_key,                    # API Key for app authentication
            consumer_secret=api_secret,              # API Secret for app authentication  
            access_token=access_token,               # User access token
            access_token_secret=access_token_secret, # User access token secret
            bearer_token=bearer_token                # Bearer token for API v2
        )
        
        # Test client connection with a simple API call
        try:
            me = client.get_me()
            if me.data:
                logging.info(f"Twitter client initialized successfully for user: @{me.data.username}")
            else:
                logging.warning("Twitter client created but user verification failed")
        except Exception as test_error:
            logging.warning(f"Twitter client created but connection test failed: {test_error}")
            
        return client
        
    except tweepy.Unauthorized as e:
        logging.error(f"Twitter API unauthorized - check credentials: {str(e)}")
        return None
    except tweepy.Forbidden as e:
        logging.error(f"Twitter API forbidden - account may be suspended: {str(e)}")
        return None
    except tweepy.NotFound as e:
        logging.error(f"Twitter API endpoint not found: {str(e)}")
        return None
    except tweepy.TooManyRequests as e:
        logging.error(f"Twitter API rate limit exceeded: {str(e)}")
        return None
    except Exception as e:
        # Handle any other client creation errors with consistent formatting
        logging.error(f"Error creating Twitter client: {type(e).__name__}: {str(e)}")
        return None

# Main execution
if __name__ == "__main__":
    print("Twitter client module ready for use!")
