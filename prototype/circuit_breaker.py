"""
Circuit breaker pattern for resilient distributed inference.

Prevents hammering failed workers and provides automatic recovery.
"""

import time
from functools import wraps
from typing import Callable, Any, Optional


class CircuitBreaker:
    """
    Circuit breaker for worker calls.
    
    States:
    - CLOSED: Normal operation, allow requests
    - OPEN: Too many failures, reject requests
    - HALF-OPEN: Testing if service recovered
    
    Args:
        failure_threshold: Number of consecutive failures before opening circuit
        recovery_timeout: Seconds to wait before trying again (half-open state)
        success_threshold: Successful calls needed to close circuit from half-open
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 1
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self.failures = 0
        self.last_failure_time: Optional[float] = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF-OPEN
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (rejecting requests)."""
        return self.state == 'OPEN'
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (allowing requests)."""
        return self.state == 'CLOSED'
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self.state == 'HALF-OPEN'
    
    def _check_timeout(self):
        """Check if recovery timeout has elapsed."""
        if self.state == 'OPEN' and self.last_failure_time:
            elapsed = time.time() - self.last_failure_time
            return elapsed >= self.recovery_timeout
        return False
    
    def _on_success(self):
        """Handle successful call."""
        self.failures = 0
        if self.state == 'HALF-OPEN':
            self.state = 'CLOSED'
    
    def _on_failure(self):
        """Handle failed call."""
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.failures >= self.failure_threshold:
            self.state = 'OPEN'
    
    def call(self, func: Callable) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Any exception from function execution
        """
        if self._check_timeout():
            self.state = 'HALF-OPEN'
        
        try:
            result = func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator syntax."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func)(*args, **kwargs)
        return wrapper


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    success_threshold: int = 1
) -> Callable:
    """
    Decorator for adding circuit breaker to functions.
    
    Args:
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds before retrying
        success_threshold: Successes needed to close circuit
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        cb = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            success_threshold=success_threshold
        )
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            if cb.is_open:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is open for {func.__name__}. "
                    f"Last failure: {cb.last_failure_time}, "
                    f"Timeout: {cb.recovery_timeout}s"
                )
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                cb._on_failure()
                raise
        
        return wrapper
    
    return decorator
