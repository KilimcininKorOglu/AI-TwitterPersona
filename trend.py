import requests              # For HTTP requests to trending topics API
from bs4 import BeautifulSoup    # For HTML parsing and data extraction
import os                    # For environment variable access
from config import get_config  # Centralized configuration

# Trending Topics Configuration - using centralized config management

def fetch_trend():
    """
    Fetch raw HTML content from the trending topics website.
    
    Returns:
        str or None: HTML content if successful, None if any error occurs
    """
    # Get URL from centralized configuration (cached automatically)
    url = get_config('TRENDS_URL', "https://xtrends.iamrohit.in/turkey")
    try:
        # Make HTTP request with 10-second timeout to prevent hanging
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            # Return raw HTML content for parsing
            content = response.text
            return content 
        else:
            # Handle non-200 HTTP status codes
            print(f"[!] HTTP Error {response.status_code}: Could not fetch trends from {url}")
            return None
        
    except requests.exceptions.Timeout:
        # Handle request timeout (>10 seconds)
        print(f"[!] Timeout error: Request to {url} took too long")
        return None
    except requests.exceptions.ConnectionError:
        # Handle network connection issues
        print(f"[!] Connection error: Could not connect to {url}")
        return None
    except requests.exceptions.RequestException as e:
        # Handle other HTTP-related errors
        print(f"[!] Request error: {e}")
        return None
    except Exception as e:
        # Handle any unexpected errors
        print(f"[!] Unexpected error while fetching trends: {e}")
        return None

def get_trending_hashtags(html_content, limit):
    """
    Parse HTML content and extract trending hashtag information.
    
    Args:
        html_content (str): Raw HTML from trends website
        limit (int): Maximum number of trends to extract
        
    Returns:
        list: List of dictionaries containing trend data (name, url, tweet_count)
    """
    # Parse HTML using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    trends = []
    
    # Find all table rows containing trend data
    rows = soup.select('tbody tr')
    
    # Extract data from each row up to the specified limit
    for row in rows[:limit]:
        # Look for the tweet link element
        trend_link = row.find('a', class_='tweet')
        if trend_link:
            # Extract trend name, URL, and tweet count
            trend_name = trend_link.text.strip()           # Clean hashtag/topic name
            trend_url = trend_link['href']                 # Twitter search URL
            tweet_count = trend_link.get('tweetcount', 'N/A')  # Number of tweets
            
            # Store structured trend data
            trends.append({
                'name': trend_name,
                'url': trend_url,
                'tweet_count': tweet_count
            })
    return trends

def is_english_or_turkish(text):
    """
    Check if text contains only English/ASCII characters or Turkish characters using proper Unicode handling.
    This allows English and Turkish trends while filtering out other languages (Arabic, Cyrillic, etc.)
    Uses Unicode categories for better Turkish character support.
    
    Args:
        text (str): Text to check
        
    Returns:
        bool: True if all characters are English or Turkish, False otherwise
    """
    import unicodedata
    
    # Extended Turkish character set including all possible variations
    turkish_chars = set('ğüşıöçĞÜŞİÖÇâêîôûÂÊÎÔÛ')
    
    for char in text:
        # Allow ASCII characters (English letters, numbers, punctuation)
        if ord(char) < 128:
            continue
            
        # Allow Turkish-specific characters
        if char in turkish_chars:
            continue
            
        # Use Unicode category for better character classification
        try:
            category = unicodedata.category(char)
            char_name = unicodedata.name(char, '')
            
            # Allow Latin script letters (includes accented characters)
            if category.startswith('L') and 'LATIN' in char_name:
                continue
                
            # Allow common punctuation and symbols
            if category in ['Pd', 'Po', 'Ps', 'Pe', 'Pc', 'Sm', 'Zs']:
                continue
                
        except (ValueError, KeyError):
            # If Unicode info unavailable, be conservative
            pass
            
        # Reject characters from other scripts (Arabic, Cyrillic, etc.)
        return False
        
    return True

def test_turkish_character_filtering():
    """Test the Turkish character filtering with various examples"""
    test_cases = [
        ("Teknoloji", True),  # Turkish word
        ("Müzik", True),     # Turkish with ü
        ("İstanbul", True),  # Turkish with İ
        ("Çiğdem", True),    # Turkish with Ç and ğ
        ("Hello World", True), # English
        ("Şarkı söyle", True), # Turkish with ş and ö
        ("مرحبا", False),    # Arabic
        ("Привет", False),   # Russian
        ("你好", False),      # Chinese
        ("AI & Tech", True), # English with symbols
        ("Türkiye'de", True) # Turkish with apostrophe
    ]
    
    print("[INFO] Testing Turkish character filtering:")
    for text, expected in test_cases:
        result = is_english_or_turkish(text)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{text}': {result} (expected: {expected})")
    
    return all(is_english_or_turkish(text) == expected for text, expected in test_cases)

def get_EnglishTrend(htmlContent, limit=5):
    """
    Extract English and Turkish trending topics from HTML content.
    
    Args:
        htmlContent (str): Raw HTML from trends website
        limit (int): Maximum number of English/Turkish trends to return (default: 5)
        
    Returns:
        list: List of English and Turkish trending topics (filtered and limited)
    """
    # Get all trends (up to 15 for better filtering options)
    allTrends = get_trending_hashtags(htmlContent, 15)
    
    # Filter for English and Turkish trends using character check
    english_turkish_Trends = [trend for trend in allTrends if is_english_or_turkish(trend['name'])]
    
    # Return only the requested number of trends
    return english_turkish_Trends[:limit]

def prepareTrend(limit):
    """
    Main function to fetch and format trending topics for the bot.
    
    Args:
        limit (int): Maximum number of trends to return
        
    Returns:
        list or None: List of formatted trend strings, or None if error
        Format: "1. #TrendName (123K Tweets) URL: https://twitter.com/..."
    """
    # Fetch raw HTML content from trends website
    html = fetch_trend()
    if html:
        # Get English trends from the HTML
        trends_list = get_EnglishTrend(html, limit)
        lines = []
        
        # Format each trend into a readable string
        for idx, trend in enumerate(trends_list, 1):
            formatted_trend = f"{idx}. {trend['name']} ({trend['tweet_count']} Tweets) URL: {trend['url']}"
            lines.append(formatted_trend)
        
        return lines
    return None  # Return None if HTML fetch failed

# Main execution
if __name__ == "__main__":
    print("Trending topics module ready for use!")
