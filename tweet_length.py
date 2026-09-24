"""Tweet length rules shared by the bot and the dashboard."""

import re

TWEET_MAX_LENGTH = 280  # Twitter's character limit for a single tweet
TCO_URL_LENGTH = 23  # Every URL is counted as a t.co link of this length
URL_PATTERN = re.compile(r'https?://[^\s]+')

# Twitter counts code points in these ranges as 1 and every other code point
# (CJK, emoji, ...) as 2 (twitter-text v3 weighted ranges). Emoji sequences
# joined with U+200D are counted per code point, which can only over-count.
SINGLE_WEIGHT_RANGES = ((0x0000, 0x10FF), (0x2000, 0x200D), (0x2010, 0x201F), (0x2032, 0x2037))


def _char_weight(char):
    code = ord(char)
    return 1 if any(low <= code <= high for low, high in SINGLE_WEIGHT_RANGES) else 2


def tweet_length(text):
    """Return the weighted length Twitter counts for text, with each URL counted as a t.co link."""
    urls = URL_PATTERN.findall(text)
    without_urls = URL_PATTERN.sub('', text)
    return sum(_char_weight(char) for char in without_urls) + TCO_URL_LENGTH * len(urls)


def fits_in_tweet(text):
    """Return True when text is within Twitter's character limit."""
    return tweet_length(text) <= TWEET_MAX_LENGTH
