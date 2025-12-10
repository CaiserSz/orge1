"""
Retry Logic Module
Created: 2025-12-10
Last Modified: 2025-12-10 18:30:00
Version: 1.0.0
Description: Retry logic with exponential backoff for ESP32 communication
"""

import time
from enum import Enum
from typing import Callable, Optional, TypeVar, Any
from functools import wraps

T = TypeVar("T")


class RetryStrategy(Enum):
    """Retry strategies"""

    LINEAR = "linear"  # Constant delay
    EXPONENTIAL = "exponential"  # Exponential backoff
    FIBONACCI = "fibonacci"  # Fibonacci backoff


class RetryConfig:
    """Retry configuration"""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 0.1,
        max_delay: float = 5.0,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        multiplier: float = 2.0,
    ):
        """
        Retry configuration

        Args:
            max_retries: Maximum number of retries (default: 3)
            initial_delay: Initial delay in seconds (default: 0.1)
            max_delay: Maximum delay in seconds (default: 5.0)
            strategy: Retry strategy (default: EXPONENTIAL)
            multiplier: Multiplier for exponential backoff (default: 2.0)
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.strategy = strategy
        self.multiplier = multiplier

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for retry attempt

        Args:
            attempt: Retry attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        if self.strategy == RetryStrategy.LINEAR:
            return min(self.initial_delay, self.max_delay)
        elif self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.initial_delay * (self.multiplier**attempt)
            return min(delay, self.max_delay)
        elif self.strategy == RetryStrategy.FIBONACCI:
            # Fibonacci sequence: 0, 1, 1, 2, 3, 5, 8, ...
            fib = self._fibonacci(attempt + 1)
            delay = self.initial_delay * fib
            return min(delay, self.max_delay)
        else:
            return self.initial_delay

    @staticmethod
    def _fibonacci(n: int) -> int:
        """Calculate Fibonacci number"""
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b


def retry_with_backoff(
    func: Callable[..., T],
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> Callable[..., T]:
    """
    Retry decorator with exponential backoff

    Args:
        func: Function to retry
        config: Retry configuration (default: RetryConfig())
        on_retry: Callback function called on retry (attempt, exception)

    Returns:
        Decorated function
    """
    if config is None:
        config = RetryConfig()

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        last_exception = None

        for attempt in range(config.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt < config.max_retries:
                    delay = config.calculate_delay(attempt)
                    if on_retry:
                        on_retry(attempt, e)
                    time.sleep(delay)
                else:
                    # Last attempt failed
                    raise last_exception

        # Should not reach here, but just in case
        raise last_exception

    return wrapper


def retry_function(
    func: Callable[..., T],
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> T:
    """
    Retry a function call with exponential backoff

    Args:
        func: Function to retry
        config: Retry configuration (default: RetryConfig())
        on_retry: Callback function called on retry (attempt, exception)

    Returns:
        Function result

    Raises:
        Exception: Last exception if all retries fail
    """
    if config is None:
        config = RetryConfig()

    last_exception = None

    for attempt in range(config.max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e

            if attempt < config.max_retries:
                delay = config.calculate_delay(attempt)
                if on_retry:
                    on_retry(attempt, e)
                time.sleep(delay)
            else:
                # Last attempt failed
                raise last_exception

    # Should not reach here, but just in case
    raise last_exception


# Default retry configurations for different operations
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    initial_delay=0.1,
    max_delay=5.0,
    strategy=RetryStrategy.EXPONENTIAL,
    multiplier=2.0,
)

QUICK_RETRY_CONFIG = RetryConfig(
    max_retries=2,
    initial_delay=0.05,
    max_delay=1.0,
    strategy=RetryStrategy.EXPONENTIAL,
    multiplier=2.0,
)

SLOW_RETRY_CONFIG = RetryConfig(
    max_retries=5,
    initial_delay=0.5,
    max_delay=10.0,
    strategy=RetryStrategy.EXPONENTIAL,
    multiplier=2.0,
)
