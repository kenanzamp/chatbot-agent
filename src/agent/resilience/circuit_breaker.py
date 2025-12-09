"""
Circuit breaker implementation for fault tolerance.
"""

from enum import Enum
from datetime import datetime, timedelta
from threading import Lock
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking calls
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Prevents cascading failures by tracking errors.
    
    States:
    - CLOSED: Normal operation, tracking failures
    - OPEN: Blocking all calls after threshold exceeded
    - HALF_OPEN: Allowing test calls to check recovery
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
        name: str = "default"
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.name = name
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure: Optional[datetime] = None
        self._lock = Lock()
    
    @property
    def state(self) -> CircuitState:
        """Get current state, transitioning if needed."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
            return self._state
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try recovery."""
        if self._last_failure is None:
            return False
        elapsed = datetime.now() - self._last_failure
        return elapsed > timedelta(seconds=self.recovery_timeout)
    
    def check(self):
        """
        Check if a call should proceed.
        
        Raises:
            CircuitBreakerOpen: If circuit is open
        """
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpen(
                f"Circuit breaker '{self.name}' is open. "
                f"Will retry in {self.recovery_timeout}s."
            )
    
    def record_success(self):
        """Record a successful call."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    logger.info(f"Circuit breaker '{self.name}' recovered to CLOSED")
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
            else:
                # Reset failure count on success in closed state
                self._failure_count = 0
    
    def record_failure(self):
        """Record a failed call."""
        with self._lock:
            self._failure_count += 1
            self._last_failure = datetime.now()
            
            if self._state == CircuitState.HALF_OPEN:
                logger.warning(f"Circuit breaker '{self.name}' failed during recovery, reopening")
                self._state = CircuitState.OPEN
            elif self._failure_count >= self.failure_threshold:
                logger.warning(f"Circuit breaker '{self.name}' opened after {self._failure_count} failures")
                self._state = CircuitState.OPEN
    
    def reset(self):
        """Manually reset the circuit breaker."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure = None
            logger.info(f"Circuit breaker '{self.name}' manually reset")
