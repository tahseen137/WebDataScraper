"""
Configuration settings for WebDataScraper.
All scraper settings can be customized here.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class ScraperConfig:
    """Configuration for web scraping behavior."""

    # Rate limiting
    DEFAULT_DELAY = float(os.getenv('SCRAPER_DELAY', '2.0'))  # Seconds between requests
    MIN_DELAY = float(os.getenv('SCRAPER_MIN_DELAY', '1.0'))  # Minimum delay
    MAX_DELAY = float(os.getenv('SCRAPER_MAX_DELAY', '10.0'))  # Maximum delay

    # Retry settings
    MAX_RETRIES = int(os.getenv('SCRAPER_MAX_RETRIES', '3'))
    RETRY_BACKOFF_FACTOR = float(os.getenv('SCRAPER_RETRY_BACKOFF', '2.0'))  # Exponential backoff multiplier
    RETRY_STATUSES = [429, 500, 502, 503, 504]  # HTTP status codes to retry

    # Request settings
    TIMEOUT = int(os.getenv('SCRAPER_TIMEOUT', '15'))  # Request timeout in seconds
    MAX_CONNECTIONS = int(os.getenv('SCRAPER_MAX_CONNECTIONS', '10'))  # Max concurrent connections

    # User agent
    USER_AGENT = os.getenv(
        'SCRAPER_USER_AGENT',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )

    # Headers
    HEADERS = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-CA,en;q=0.9,fr-CA;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    # Data quality
    MIN_CONFIDENCE_THRESHOLD = float(os.getenv('MIN_CONFIDENCE_THRESHOLD', '0.3'))

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_TO_FILE = os.getenv('LOG_TO_FILE', 'true').lower() == 'true'
    LOG_DIR = os.getenv('LOG_DIR', 'logs')


class DatabaseConfig:
    """Configuration for Supabase database."""

    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')


# Scraping sources configuration
SCRAPING_SOURCES = {
    'creditcardgenius': {
        'enabled': True,
        'urls': [
            ("https://creditcardgenius.ca/best-credit-cards/cash-back", "cashback"),
            ("https://creditcardgenius.ca/best-credit-cards/travel", "travel"),
            ("https://creditcardgenius.ca/best-credit-cards/rewards", "rewards"),
            ("https://creditcardgenius.ca/best-credit-cards/no-fee", "no-fee"),
            ("https://creditcardgenius.ca/best-credit-cards/groceries", "groceries"),
        ]
    },
    'ratehub': {
        'enabled': True,
        'urls': [
            "https://www.ratehub.ca/credit-cards/cash-back",
            "https://www.ratehub.ca/credit-cards/travel",
            "https://www.ratehub.ca/credit-cards/rewards",
            "https://www.ratehub.ca/credit-cards/no-fee",
        ]
    },
    'moneysense': {
        'enabled': True,
        'urls': [
            "https://www.moneysense.ca/spend/credit-cards/best-credit-cards-in-canada/",
            "https://www.moneysense.ca/spend/credit-cards/best-cash-back-credit-cards-in-canada/",
            "https://www.moneysense.ca/spend/credit-cards/best-travel-credit-cards-in-canada/",
        ]
    },
    'nerdwallet': {
        'enabled': True,
        'urls': [
            "https://www.nerdwallet.com/ca/credit-cards/best-cash-back-credit-cards",
            "https://www.nerdwallet.com/ca/credit-cards/best-travel-credit-cards",
            "https://www.nerdwallet.com/ca/credit-cards/best-rewards-credit-cards",
            "https://www.nerdwallet.com/ca/credit-cards/best-no-fee-credit-cards",
        ]
    },
    'greedyrates': {
        'enabled': True,
        'urls': [
            "https://www.greedyrates.ca/blog/best-cash-back-credit-cards-canada/",
            "https://www.greedyrates.ca/blog/best-travel-credit-cards-canada/",
            "https://www.greedyrates.ca/blog/best-rewards-credit-cards-canada/",
            "https://www.greedyrates.ca/blog/best-no-fee-credit-cards-canada/",
        ]
    }
}
