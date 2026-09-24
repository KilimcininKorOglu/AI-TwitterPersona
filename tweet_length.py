"""Tweet length rules shared by the bot and the dashboard."""

import re

TWEET_MAX_LENGTH = 280  # Twitter's character limit for a single tweet
TCO_URL_LENGTH = 23  # Every URL is counted as a t.co link of this length
URL_PATTERN = re.compile(r'https?://[^\s]+')


def tweet_length(text):
    """Return the length Twitter counts for text, with each URL counted as a t.co link."""
    length = len(text)
    for url in URL_PATTERN.findall(text):
        length = length - len(url) + TCO_URL_LENGTH
    return length


def fits_in_tweet(text):
    """Return True when text is within Twitter's character limit."""
    return tweet_length(text) <= TWEET_MAX_LENGTH
