"""
Error handling utilities for WebDataScraper.
Provides custom exceptions and error recovery strategies.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Base exception for scraper errors."""
    pass


class NetworkError(ScraperError):
    """Raised when network requests fail."""
    pass


class ParseError(ScraperError):
    """Raised when parsing HTML/data fails."""
    pass


class ValidationError(ScraperError):
    """Raised when data validation fails."""
    pass


class DatabaseError(ScraperError):
    """Raised when database operations fail."""
    pass


class ConfigurationError(ScraperError):
    """Raised when configuration is invalid."""
    pass


class ErrorTracker:
    """
    Tracks errors across scraping sessions for monitoring and debugging.
    """

    def __init__(self):
        """Initialize error tracker."""
        self.errors = []
        self.error_counts = {}
        self.session_start = datetime.now()

    def record_error(
        self,
        error_type: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        severity: str = "error"
    ):
        """
        Record an error occurrence.

        Args:
            error_type: Type/category of error (e.g., "network", "parse", "validation")
            message: Error message
            context: Additional context (URL, card name, etc.)
            severity: Error severity ("warning", "error", "critical")
        """
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': error_type,
            'message': message,
            'context': context or {},
            'severity': severity
        }

        self.errors.append(error_entry)

        # Update counts
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

        # Log the error
        log_func = getattr(logger, severity, logger.error)
        context_str = f" | Context: {context}" if context else ""
        log_func(f"[{error_type}] {message}{context_str}")

    def get_summary(self) -> Dict[str, Any]:
        """
        Get error summary statistics.

        Returns:
            Dictionary with error statistics
        """
        duration = (datetime.now() - self.session_start).total_seconds()

        return {
            'session_duration_seconds': duration,
            'total_errors': len(self.errors),
            'error_counts_by_type': self.error_counts.copy(),
            'recent_errors': self.errors[-10:],  # Last 10 errors
            'errors_per_minute': len(self.errors) / (duration / 60) if duration > 0 else 0
        }

    def get_errors_by_type(self, error_type: str) -> list:
        """
        Get all errors of a specific type.

        Args:
            error_type: Type of error to filter by

        Returns:
            List of error entries
        """
        return [e for e in self.errors if e['type'] == error_type]

    def clear(self):
        """Clear all recorded errors."""
        self.errors.clear()
        self.error_counts.clear()
        self.session_start = datetime.now()
        logger.info("Error tracker cleared")

    def has_critical_errors(self) -> bool:
        """
        Check if any critical errors have been recorded.

        Returns:
            True if critical errors exist
        """
        return any(e['severity'] == 'critical' for e in self.errors)


class ErrorRecovery:
    """
    Provides error recovery strategies for common failure scenarios.
    """

    @staticmethod
    def handle_network_error(url: str, error: Exception, error_tracker: Optional[ErrorTracker] = None):
        """
        Handle network-related errors.

        Args:
            url: The URL that failed
            error: The exception that occurred
            error_tracker: Optional error tracker to record the error

        Returns:
            None (logs the error and optionally tracks it)
        """
        logger.error(f"Network error accessing {url}: {str(error)[:200]}", exc_info=True)

        if error_tracker:
            error_tracker.record_error(
                error_type="network",
                message=str(error)[:200],
                context={'url': url},
                severity="error"
            )

    @staticmethod
    def handle_parse_error(
        source: str,
        element_type: str,
        error: Exception,
        error_tracker: Optional[ErrorTracker] = None
    ):
        """
        Handle HTML/data parsing errors.

        Args:
            source: Source name (e.g., "ratehub", "moneysense")
            element_type: Type of element being parsed
            error: The exception that occurred
            error_tracker: Optional error tracker to record the error

        Returns:
            None (logs the error and optionally tracks it)
        """
        logger.warning(
            f"Parse error from {source} parsing {element_type}: {str(error)[:200]}"
        )

        if error_tracker:
            error_tracker.record_error(
                error_type="parse",
                message=str(error)[:200],
                context={'source': source, 'element_type': element_type},
                severity="warning"
            )

    @staticmethod
    def handle_validation_error(
        card_key: str,
        issues: list,
        error_tracker: Optional[ErrorTracker] = None
    ):
        """
        Handle data validation errors.

        Args:
            card_key: Card identifier
            issues: List of validation issues
            error_tracker: Optional error tracker to record the error

        Returns:
            None (logs the error and optionally tracks it)
        """
        logger.warning(f"Validation issues for {card_key}: {issues}")

        if error_tracker:
            error_tracker.record_error(
                error_type="validation",
                message=f"{len(issues)} validation issues",
                context={'card_key': card_key, 'issues': issues},
                severity="warning"
            )

    @staticmethod
    def handle_database_error(
        operation: str,
        error: Exception,
        error_tracker: Optional[ErrorTracker] = None
    ):
        """
        Handle database operation errors.

        Args:
            operation: Database operation that failed
            error: The exception that occurred
            error_tracker: Optional error tracker to record the error

        Returns:
            None (logs the error and optionally tracks it)
        """
        logger.error(f"Database error during {operation}: {str(error)[:200]}", exc_info=True)

        if error_tracker:
            error_tracker.record_error(
                error_type="database",
                message=str(error)[:200],
                context={'operation': operation},
                severity="critical"
            )
