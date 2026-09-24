import tweepy               # Twitter API library for Python
from config import get_config  # Centralized configuration
import logging  # For secure logging

# Credential keys read from token.env on every get_client() call
CREDENTIAL_KEYS = ("api_key", "api_secret", "access_token", "access_token_secret", "bearer_token")

# Cached client and the credentials it was built with
client = None
_client_credentials = None

def read_credentials():
    """Read the current Twitter API credentials from configuration."""
    return {key: get_config(key) for key in CREDENTIAL_KEYS}

def validate_credentials(credentials):
    """Validate Twitter API credentials with standardized error messages"""
    # Identify missing credentials or placeholder values (starting with "YOUR_")
    missing_credentials = [key for key, value in credentials.items()
                           if not value or value.startswith("YOUR_")]
    if missing_credentials:
        error_msg = f"Missing Twitter API credentials: {', '.join(missing_credentials)}"
        logging.error(error_msg)
        logging.info("Required credentials: api_key, api_secret, access_token, access_token_secret, bearer_token")
        logging.info("Get your credentials from: https://developer.twitter.com/en/portal/dashboard")
        logging.info("Update them in token.env file")
        return False

    # Validate credential format
    if len(credentials["api_key"]) < 10:
        logging.error("API key appears to be invalid (too short)")
        return False
    if not credentials["bearer_token"].startswith('AAAA'):
        logging.error("Bearer token appears to be invalid (wrong format)")
        return False

    return True

def build_client(credentials):
    """Create a Tweepy client from credentials and log a connection test result."""
    # Initialize Tweepy client with all authentication methods
    new_client = tweepy.Client(
        consumer_key=credentials["api_key"],                    # API Key for app authentication
        consumer_secret=credentials["api_secret"],              # API Secret for app authentication
        access_token=credentials["access_token"],               # User access token
        access_token_secret=credentials["access_token_secret"], # User access token secret
        bearer_token=credentials["bearer_token"]                # Bearer token for API v2
    )

    # Test client connection with a simple API call
    try:
        me = new_client.get_me()
        if me.data:
            logging.info(f"Twitter client initialized successfully for user: @{me.data.username}")
        else:
            logging.warning("Twitter client created but user verification failed")
    except Exception as test_error:
        logging.warning(f"Twitter client created but connection test failed: {test_error}")
    return new_client

def get_client():
    """
    Create and return a configured Twitter API client using Tweepy.

    This function initializes a Tweepy Client with all required authentication
    credentials for both Twitter API v1.1 and v2 endpoints. Credentials are read
    on every call, and the cached client is rebuilt when they change.

    Returns:
        tweepy.Client: Authenticated Twitter client ready for API calls or None if credentials missing

    Note:
        This function validates credentials before creating the client.
    """
    global client, _client_credentials

    credentials = read_credentials()
    if client is not None and credentials == _client_credentials:
        return client  # Already initialized with the current credentials

    # Validate credentials first
    if not validate_credentials(credentials):
        client = None
        _client_credentials = None
        return None

    try:
        client = build_client(credentials)
        _client_credentials = credentials
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
