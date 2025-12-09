"""
Retry utilities with exponential backoff.
"""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError
)
import logging
from typing import Tuple, Type

logger = logging.getLogger(__name__)


def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 30.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (ConnectionError, TimeoutError)
):
    """
    Decorator factory for adding retry logic.
    
    Args:
        max_attempts: Maximum retry attempts
        min_wait: Minimum wait between retries (seconds)
        max_wait: Maximum wait between retries (seconds)
        retryable_exceptions: Exception types to retry on
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(retryable_exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )


# Pre-configured retry for LLM API calls
llm_retry = with_retry(
    max_attempts=3,
    min_wait=1.0,
    max_wait=60.0,
    retryable_exceptions=(ConnectionError, TimeoutError, OSError)
)


# Pre-configured retry for external services
external_service_retry = with_retry(
    max_attempts=5,
    min_wait=0.5,
    max_wait=30.0,
    retryable_exceptions=(ConnectionError, TimeoutError)
)
