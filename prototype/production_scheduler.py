# prototype/production_scheduler.py (ENHANCED)
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import requests

@dataclass
class WorkerHealthMetrics:
    """Real-time worker health metrics."""

    gpu_utilization: float = 0.0
    memory_free_gb: float = 0.0
    cpu_utilization: float = 0.0
    inference_queue_depth: int = 0
    p50_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    is_healthy: bool = True
    last_error: Optional[str] = None

    def __post_init__(self):
        # Validate ranges
        if not (0 <= self.gpu_utilization <= 1):
            raise ValueError("GPU utilization must be 0-1")

class ProductionScheduler:
    """Production-grade cost-aware scheduler with real-time metrics."""

    def __init__(
        self,
        workers: List[str],
        health_endpoint: str = "/metrics",
        health_interval: float = 5.0,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 30,
    ):
        self.workers = [w for w in workers if w.startswith("http")]
        self.health_endpoint = health_endpoint
        self.health_interval = health_interval

        # Worker profiles with real-time metrics
        self.worker_metrics: Dict[str, WorkerHealthMetrics] = {}
        self._metrics_lock = threading.Lock()

        # Circuit breaker state
        self.circuit_breakers: Dict[str, CircuitBreaker] = {
            w: CircuitBreaker(
                failure_threshold=circuit_breaker_threshold,
                timeout=circuit_breaker_timeout,
            )
            for w in workers
        }

        # Last health check time
        self._last_health_check: Dict[str, float] = {w: time.time() for w in workers}

    def update_worker_metrics(self):
        """Poll all workers for real-time metrics."""
        for worker in self.workers:
            try:
                resp = requests.get(f"{worker}{self.health_endpoint}", timeout=5)
                if resp.status_code == 200:
                    metrics_data = resp.json()
                    worker_url = worker.replace("/metrics", "")

                    # Parse Prometheus metrics
                    gpu_util = self._parse_metric(metrics_data, "gpu_utilization", 0.0)
                    mem_free_gb = self._parse_metric(
                        metrics_data, "memory_free_gb", 0.0
                    )

                    self.worker_metrics[worker_url] = WorkerHealthMetrics(
                        gpu_utilization=gpu_util,
                        memory_free_gb=mem_free_gb,
                        cpu_utilization=self._parse_metric(
                            metrics_data, "cpu_utilization", 0.0
                        ),
                        inference_queue_depth=self._parse_metric(
                            metrics_data, "inference_queue", 0
                        ),
                        p50_latency_ms=self._parse_metric(
                            metrics_data, "p50_latency_ms", 0.0
                        ),
                        p99_latency_ms=self._parse_metric(
                            metrics_data, "p99_latency_ms", 0.0
                        ),
                    )

                self._last_health_check[worker] = time.time()
            except Exception as e:
                # Mark worker unhealthy
                if worker_url not in self.worker_metrics:
                    self.worker_metrics[worker_url] = WorkerHealthMetrics(
                        is_healthy=False, last_error=str(e)
                    )

    def _parse_metric(self, metrics_dict: dict, metric_name: str, default) -> float:
        """Parse Prometheus-style metric from JSON."""
        key = f"{metric_name}_sum" if "_sum" not in metric_name else metric_name
        count_key = (
            f"{metric_name}_count" if "_count" not in metric_name else metric_name
        )

        if count_key in metrics_dict and metrics_dict[count_key] > 0:
            return metrics_dict[key] / metrics_dict[count_key]
        return default

    def select_best_worker(
        self, slice_metadata: SliceMetadata, target_latency_ms: Optional[float] = None
    ) -> Optional[str]:
        """Select best worker using cost model with real-time metrics."""

        # Update all worker metrics if stale
        now = time.time()
        for worker in self.workers:
            if now - self._last_health_check[worker] > self.health_interval * 2:
                self.update_worker_metrics()

        # Filter healthy workers with available memory
        candidates = [
            w
            for w, m in self.worker_metrics.items()
            if m.is_healthy
            and m.memory_free_gb >= slice_metadata.activation_size_bytes / (1024**3)
        ]

        if not candidates:
            return None

        # Sort by composite cost score
        scored_workers = []
        for worker_url, metrics in self.worker_metrics.items():
            if not metrics.is_healthy:
                continue

            # Check circuit breaker
            if self.circuit_breakers[worker_url].is_open():
                continue

            # Compute cost score (lower is better)
            gpu_penalty = metrics.gpu_utilization * 10  # Penalize high GPU util
            latency_penalty = metrics.p99_latency_ms / 100 if target_latency_ms else 0

            cost_score = (
                metrics.gpu_utilization  # Normalized GPU util
                + latency_penalty  # Latency penalty
                + metrics.cpu_utilization * 2  # CPU pressure
            )

            scored_workers.append((worker_url, cost_score))

        if not scored_workers:
            return None

        # Select worker with lowest cost score
        scored_workers.sort(key=lambda x: x[1])
        best_worker = scored_workers[0][0]

        # Record placement decision for telemetry
        self.record_placement_decision(slice_metadata.slice_id, best_worker)

        return best_worker

    def record_placement_decision(self, slice_id: str, worker_url: str):
        """Record placement for telemetry/observability."""
        # Emit to Prometheus/OpenTelemetry
        pass

    def record_failure(self, worker_url: str):
        """Record request failure to circuit breaker."""
        self.circuit_breakers[worker_url].record_failure()
