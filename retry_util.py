"""
Retry utility with exponential backoff for WebDataScraper.
Provides decorators and utilities for retrying failed operations.
"""

import time
import logging
from functools import wraps
from typing import Callable, Optional, Tuple, Type
import requests

logger = logging.getLogger(__name__)


class RetryException(Exception):
    """Exception raised when all retry attempts are exhausted."""
    pass


def retry_with_backoff(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    retry_on: Tuple[Type[Exception], ...] = (requests.RequestException,),
    retry_statuses: Tuple[int, ...] = (429, 500, 502, 503, 504),
    on_retry: Optional[Callable] = None
):
    """
    Decorator to retry a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff (delay = backoff_factor ^ attempt)
        retry_on: Tuple of exception types to retry on
        retry_statuses: HTTP status codes that should trigger a retry
        on_retry: Optional callback function called on each retry with (attempt, exception, delay)

    Example:
        @retry_with_backoff(max_retries=3, backoff_factor=2.0)
        def fetch_data(url):
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)

                    # Check if result is a Response object with a status code
                    if hasattr(result, 'status_code'):
                        if result.status_code in retry_statuses:
                            raise requests.HTTPError(
                                f"HTTP {result.status_code}",
                                response=result
                            )

                    # Success!
                    if attempt > 0:
                        logger.info(f"{func.__name__} succeeded after {attempt} retries")
                    return result

                except retry_on as e:
                    last_exception = e

                    # Don't retry on the last attempt
                    if attempt >= max_retries:
                        break

                    # Calculate backoff delay
                    delay = backoff_factor ** attempt
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)[:200]}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    # Call on_retry callback if provided
                    if on_retry:
                        on_retry(attempt, e, delay)

                    # Wait before retrying
                    time.sleep(delay)

            # All retries exhausted
            error_msg = f"{func.__name__} failed after {max_retries + 1} attempts"
            logger.error(f"{error_msg}: {str(last_exception)[:200]}")
            raise RetryException(error_msg) from last_exception

        return wrapper
    return decorator


class RetrySession(requests.Session):
    """
    Requests Session with built-in retry logic.
    Automatically retries failed requests with exponential backoff.
    """

    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        retry_statuses: Tuple[int, ...] = (429, 500, 502, 503, 504),
        timeout: int = 15,
        **kwargs
    ):
        """
        Initialize retry session.

        Args:
            max_retries: Maximum number of retry attempts
            backoff_factor: Multiplier for exponential backoff
            retry_statuses: HTTP status codes to retry on
            timeout: Default timeout for requests
            **kwargs: Additional arguments passed to requests.Session
        """
        super().__init__(**kwargs)
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_statuses = retry_statuses
        self.default_timeout = timeout

    def request(self, method: str, url: str, **kwargs):
        """
        Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL to request
            **kwargs: Additional arguments for the request

        Returns:
            Response object

        Raises:
            RetryException: If all retries are exhausted
        """
        # Set default timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.default_timeout

        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                response = super().request(method, url, **kwargs)

                # Check if we should retry based on status code
                if response.status_code in self.retry_statuses:
                    if attempt >= self.max_retries:
                        logger.error(
                            f"HTTP {response.status_code} for {url} after {self.max_retries + 1} attempts"
                        )
                        return response  # Return the error response on last attempt

                    delay = self.backoff_factor ** attempt
                    logger.warning(
                        f"HTTP {response.status_code} for {url} "
                        f"(attempt {attempt + 1}/{self.max_retries + 1}). "
                        f"Retrying in {delay:.2f}s..."
                    )
                    time.sleep(delay)
                    continue

                # Success!
                if attempt > 0:
                    logger.info(f"Request to {url} succeeded after {attempt} retries")

                return response

            except requests.RequestException as e:
                last_exception = e

                # Don't retry on the last attempt
                if attempt >= self.max_retries:
                    break

                delay = self.backoff_factor ** attempt
                logger.warning(
                    f"Request to {url} failed (attempt {attempt + 1}/{self.max_retries + 1}): {str(e)[:200]}. "
                    f"Retrying in {delay:.2f}s..."
                )
                time.sleep(delay)

        # All retries exhausted
        error_msg = f"Request to {url} failed after {self.max_retries + 1} attempts"
        logger.error(f"{error_msg}: {str(last_exception)[:200]}")
        raise RetryException(error_msg) from last_exception


def safe_execute(func: Callable, *args, default=None, log_error: bool = True, **kwargs):
    """
    Safely execute a function, returning a default value on error.

    Args:
        func: Function to execute
        *args: Positional arguments for the function
        default: Default value to return on error
        log_error: Whether to log errors
        **kwargs: Keyword arguments for the function

    Returns:
        Function result or default value on error

    Example:
        result = safe_execute(int, "not a number", default=0)
        # Returns 0 instead of raising ValueError
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_error:
            logger.debug(f"safe_execute failed for {func.__name__}: {str(e)[:100]}")
        return default
