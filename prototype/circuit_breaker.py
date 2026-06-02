"""
Circuit Breaker Pattern Implementation for Mohawk Inference Engine.

This module provides fault tolerance and graceful degradation by:
1. Tracking worker health via request/response patterns
2. Opening circuits after consecutive failures
3. Falling back to local execution or alternate workers
4. Automatically resetting circuits on success
"""

import time
from enum import Enum, auto
from typing import Callable, Dict, Optional, Any
import threading


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = auto()       # Normal operation, requests pass through
    OPEN = auto()         # Circuit tripped, requests fail fast
    HALF_OPEN = auto()   # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker implementation for worker health management.
    
    State Transitions:
    - CLOSED -> OPEN: After `failure_threshold` consecutive failures
    - OPEN -> HALF_OPEN: After `reset_timeout_seconds` passes
    - HALF_OPEN -> CLOSED: If request succeeds during testing period
    - HALF_OPEN -> OPEN: If request fails during testing period
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,           # Failures before opening
        reset_timeout_seconds: int = 30,      # Time to wait before retrying
        half_open_max_calls: int = 3,         # Max calls in HALF_OPEN state
        success_threshold: int = 1            # Successes needed to close
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        self.half_open_max_calls = half_open_max_calls
        self.success_threshold = success_threshold
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = threading.Lock()
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Auto-transition to HALF_OPEN after reset timeout
                if self._last_failure_time is not None:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.reset_timeout_seconds:
                        self._state = CircuitState.HALF_OPEN
                        self._half_open_calls = 0
            
            return self._state
    
    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        with self._lock:
            return self._failure_count
    
    @property
    def success_count(self) -> int:
        """Get current success count."""
        with self._lock:
            return self._success_count
    
    def record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    # Transition to CLOSED
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
            elif self._state == CircuitState.CLOSED:
                # Optional: reset failure count on success
                self._failure_count = 0
    
    def record_failure(self) -> None:
        """Record a failed call."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                # Transition back to OPEN after any failure in HALF_OPEN
                self._state = CircuitState.OPEN
                self._failure_count += 1
                self._last_failure_time = time.time()
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self.failure_threshold:
                    # Transition to OPEN
                    self._state = CircuitState.OPEN
                    self._last_failure_time = time.time()
    
    def is_call_allowed(self) -> bool:
        """Check if a call is allowed (circuit permits it)."""
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            elif self._state == CircuitState.OPEN:
                # Check reset timeout
                if self._last_failure_time is not None:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.reset_timeout_seconds:
                        self._state = CircuitState.HALF_OPEN
                        self._half_open_calls = 0
                        return True
                return False
            elif self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
        return False
    
    def execute_with_circuit_breaker(
        self,
        func: Callable[..., Any],
        *args,
        **kwargs
    ) -> Optional[Any]:
        """
        Execute function with circuit breaker protection.
        
        Returns function result if successful, None if circuit is open.
        """
        if not self.is_call_allowed():
            # Circuit is open, skip execution and record failure
            self.record_failure()
            return None
        
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise


class WorkerHealthMonitor:
    """
    Monitors health of worker nodes using circuit breakers.
    
    Supports:
    - Per-worker circuit breakers
    - Global fallback to local execution
    - Alternate worker routing
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout_seconds: int = 30,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        self.half_open_max_calls = half_open_max_calls
        
        # Per-worker circuit breakers
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Worker availability status
        self._worker_status: Dict[str, bool] = {}
        
        # Fallback configuration
        self._fallback_enabled = True
        self._local_execution_fallback = True
    
    def get_circuit_breaker(self, worker_url: str) -> CircuitBreaker:
        """Get or create circuit breaker for worker."""
        if worker_url not in self._circuit_breakers:
            self._circuit_breakers[worker_url] = CircuitBreaker(
                failure_threshold=self.failure_threshold,
                reset_timeout_seconds=self.reset_timeout_seconds,
                half_open_max_calls=self.half_open_max_calls
            )
        return self._circuit_breakers[worker_url]
    
    def record_worker_success(self, worker_url: str) -> None:
        """Record successful call to worker."""
        cb = self.get_circuit_breaker(worker_url)
        cb.record_success()
        
        # Mark worker as healthy
        self._worker_status[worker_url] = True
    
    def record_worker_failure(self, worker_url: str) -> None:
        """Record failed call to worker."""
        cb = self.get_circuit_breaker(worker_url)
        cb.record_failure()
        
        # Optionally mark worker as unhealthy after failure
        if cb.state == CircuitState.OPEN:
            self._worker_status[worker_url] = False
    
    def execute_with_fallback(
        self,
        worker_url: str,
        func: Callable[..., Any],
        *args,
        **kwargs
    ) -> Optional[Any]:
        """
        Execute function with fallback to local execution if circuit is open.
        
        Returns None if all paths fail.
        """
        cb = self.get_circuit_breaker(worker_url)
        
        try:
            # Try worker first
            result = cb.execute_with_circuit_breaker(func, *args, **kwargs)
            
            if result is not None:  # Circuit was open and we skipped execution
                return result
            
            return result
            
        except Exception:
            self.record_worker_failure(worker_url)
            
            # Check for fallback
            if self._fallback_enabled and self._local_execution_fallback:
                return self._execute_locally(*args, **kwargs)
            
            raise
    
    def _execute_locally(self, *args, **kwargs) -> Optional[Any]:
        """Execute locally (single-node fallback)."""
        # Placeholder for local execution logic
        # In production, this would run model locally without worker calls
        print(f"Fall back to local execution")
        return None
    
    def is_worker_healthy(self, worker_url: str) -> bool:
        """Check if worker is healthy (circuit closed or half-open)."""
        cb = self.get_circuit_breaker(worker_url)
        return cb.state != CircuitState.OPEN
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get health report for all workers."""
        report = {
            'timestamp': time.time(),
            'workers': {}
        }
        
        for worker_url in self._circuit_breakers:
            cb = self.get_circuit_breaker(worker_url)
            report['workers'][worker_url] = {
                'state': cb.state.name,
                'failure_count': cb.failure_count,
                'success_count': cb.success_count,
                'is_healthy': cb.state != CircuitState.OPEN,
            }
        
        return report


class AdaptiveRouting:
    """
    Routes requests to healthy workers based on circuit breaker status.
    
    Features:
    - Round-robin among healthy workers
    - Prefer workers with closed circuits
    - Avoid recently recovered workers (HALF_OPEN state)
    """
    
    def __init__(self, health_monitor: WorkerHealthMonitor):
        self.monitor = health_monitor
        self._round_robin_index = 0
        self._lock = threading.Lock()
    
    def get_healthy_worker(self, all_workers: list) -> Optional[str]:
        """Get a healthy worker from the list using round-robin."""
        with self._lock:
            healthy_workers = [
                w for w in all_workers
                if self.monitor.is_worker_healthy(w)
            ]
            
            if not healthy_workers:
                return None
            
            # Round-robin among healthy workers
            worker = healthy_workers[self._round_robin_index % len(healthy_workers)]
            self._round_robin_index += 1
            
            return worker
    
    def route_request(self, all_workers: list) -> Optional[str]:
        """Route incoming request to a healthy worker."""
        return self.get_healthy_worker(all_workers)


# Example usage and integration with existing code

class FaultTolerantController:
    """
    Controller with built-in fault tolerance via circuit breakers.
    
    Replaces or enhances prototype/controller_secure.py.
    """
    
    def __init__(self, workers):
        self.workers = workers
        self.health_monitor = WorkerHealthMonitor(
            failure_threshold=5,
            reset_timeout_seconds=30,
            half_open_max_calls=3
        )
        self.router = AdaptiveRouting(self.health_monitor)
        
        # Initialize circuit breakers for all workers
        for w in workers:
            self.health_monitor.get_circuit_breaker(w)
    
    def partition_model(self, model, num_slices=2):
        """Partition model into slices."""
        L = len(model.weights)
        per = max(1, L // num_slices)
        slices = []
        for i in range(0, L, per):
            start = i
            end = min(L, i + per)
            sub = model.slice(start, end)
            slices.append((start, end, sub))
        return slices
    
    def preload_slices(self, slices, encrypt=False):
        """Preload slices with fault tolerance."""
        assigned = []
        
        for i, (start, end, sub) in enumerate(slices):
            w = self.workers[i % len(self.workers)]
            
            # Execute with circuit breaker and fallback
            try:
                blob = sub.serialize()
                manifest = {"start": start, "end": end}
                slice_id = f"slice_{start}_{end}"
                
                payload = {
                    "slice_id": slice_id,
                    "manifest": manifest,
                    "weights_b64": "<base64-encoded-weights>",
                    "encrypted": encrypt
                }
                
                # In production, use requests.post here
                # For now, simulate success/failure for demo
                
                self.health_monitor.record_worker_success(w)
                assigned.append((slice_id, w))
                
            except Exception as e:
                self.health_monitor.record_worker_failure(w)
                print(f"Failed to preload slice {slice_id} on worker {w}: {e}")
                # Try alternate worker or skip
        
        return assigned
    
    def run_distributed(self, assigned, x_blob, encrypt=False):
        """Run distributed inference with fault tolerance."""
        current = x_blob
        
        for slice_id, w in assigned:
            try:
                # Execute with circuit breaker
                result = self.health_monitor.execute_with_fallback(
                    worker_url=w,
                    func=self._execute_on_worker,
                    slice_id=slice_id,
                    input_blob=current,
                    encrypt=encrypt
                )
                
                if result is None:  # Circuit was open, skip this slice
                    print(f"Skipping slice {slice_id} due to circuit breaker")
                    continue
                
                current = result
                
            except Exception as e:
                self.health_monitor.record_worker_failure(w)
                print(f"Error executing on worker {w}: {e}")
        
        return current
    
    def _execute_on_worker(self, slice_id, input_blob, encrypt):
        """Actual execution on worker (placeholder)."""
        # In production, this would be the actual HTTP request
        pass


if __name__ == '__main__':
    # Demo circuit breaker behavior
    
    cb = CircuitBreaker(
        failure_threshold=3,
        reset_timeout_seconds=5,
        half_open_max_calls=2
    )
    
    print(f"Initial state: {cb.state}")
    
    # Simulate failures
    for i in range(5):
        print(f"\nSimulating failure {i+1}...")
        cb.record_failure()
        print(f"State after failure: {cb.state}, Failure count: {cb.failure_count}")
    
    print(f"\nCircuit is OPEN, waiting for reset timeout...")
    time.sleep(6)  # Wait for reset
    
    print(f"\nAfter timeout, state: {cb.state}")
    
    # Simulate success in HALF_OPEN state
    cb.record_success()
    print(f"After success, state: {cb.state}, Failure count: {cb.failure_count}")
