"""
Rate limiting utility for WebDataScraper.
Implements smart rate limiting with exponential backoff and domain-based throttling.
"""

import time
import random
from collections import defaultdict
from typing import Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Adaptive rate limiter that tracks requests per domain.
    Implements exponential backoff and jitter to avoid detection.
    """

    def __init__(self, min_delay: float = 1.0, max_delay: float = 10.0, default_delay: float = 2.0):
        """
        Initialize rate limiter.

        Args:
            min_delay: Minimum delay between requests (seconds)
            max_delay: Maximum delay between requests (seconds)
            default_delay: Default delay between requests (seconds)
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.default_delay = default_delay

        # Track last request time per domain
        self._last_request_time = defaultdict(float)

        # Track consecutive errors per domain for backoff
        self._error_count = defaultdict(int)

        # Track total requests per domain
        self._request_count = defaultdict(int)

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc

    def wait(self, url: str, add_jitter: bool = True):
        """
        Wait before making a request to the given URL.

        Args:
            url: The URL to request
            add_jitter: Whether to add random jitter to avoid patterns
        """
        domain = self._get_domain(url)
        current_time = time.time()
        last_request = self._last_request_time[domain]

        # Calculate required delay
        time_since_last = current_time - last_request
        error_count = self._error_count[domain]

        # Apply exponential backoff if there were recent errors
        delay = self.default_delay
        if error_count > 0:
            delay = min(self.default_delay * (2 ** error_count), self.max_delay)
            logger.debug(f"Applying backoff for {domain}: {delay:.2f}s (errors: {error_count})")

        # Add jitter (±20%) to make requests less predictable
        if add_jitter:
            jitter = random.uniform(-0.2, 0.2) * delay
            delay = delay + jitter

        # Ensure delay is within bounds
        delay = max(self.min_delay, min(delay, self.max_delay))

        # Wait if needed
        if time_since_last < delay:
            sleep_time = delay - time_since_last
            logger.debug(f"Rate limiting {domain}: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

        # Update last request time
        self._last_request_time[domain] = time.time()
        self._request_count[domain] += 1

    def record_success(self, url: str):
        """
        Record a successful request to gradually reduce backoff.

        Args:
            url: The URL that succeeded
        """
        domain = self._get_domain(url)
        if self._error_count[domain] > 0:
            self._error_count[domain] = max(0, self._error_count[domain] - 1)
            logger.debug(f"Success for {domain}, reducing error count to {self._error_count[domain]}")

    def record_error(self, url: str):
        """
        Record a failed request to increase backoff.

        Args:
            url: The URL that failed
        """
        domain = self._get_domain(url)
        self._error_count[domain] += 1
        logger.warning(f"Error for {domain}, increasing error count to {self._error_count[domain]}")

    def reset_domain(self, url: str):
        """
        Reset rate limiting state for a domain.

        Args:
            url: URL of the domain to reset
        """
        domain = self._get_domain(url)
        self._error_count[domain] = 0
        logger.info(f"Reset rate limiting for {domain}")

    def get_stats(self, url: Optional[str] = None) -> dict:
        """
        Get rate limiting statistics.

        Args:
            url: Optional URL to get stats for specific domain

        Returns:
            Dictionary of statistics
        """
        if url:
            domain = self._get_domain(url)
            return {
                'domain': domain,
                'requests': self._request_count[domain],
                'errors': self._error_count[domain],
                'last_request': self._last_request_time[domain]
            }
        else:
            return {
                'total_domains': len(self._request_count),
                'total_requests': sum(self._request_count.values()),
                'domains': {
                    domain: {
                        'requests': self._request_count[domain],
                        'errors': self._error_count[domain]
                    }
                    for domain in self._request_count.keys()
                }
            }
