"""
Cost-Aware Scheduler for Mohawk Inference Engine.

This module implements intelligent slice placement decisions based on:
1. Device capabilities (GPU vs CPU)
2. Memory availability
3. Network latency between devices
4. Current load metrics
5. Slice characteristics (size, compute requirements)
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class WorkerProfile:
    """Worker device profile."""

    url: str
    device_type: str  # 'gpu', 'cpu', 'npu'
    gpu_model: Optional[str] = None

    # Memory (bytes)
    memory_total: int = 0
    memory_free: int = 0
    memory_reserved: int = 0

    # Compute capability
    cpu_cores: int = 0
    gpu_flops_tflops: float = 0.0  # TFLOPS

    # Network
    network_interface: str = "eth0"
    network_bandwidth_gbps: float = 1.0

    # Health
    is_healthy: bool = True
    last_error: Optional[str] = None

    # Current load
    current_gpu_utilization: float = 0.0  # 0-1
    current_cpu_utilization: float = 0.0  # 0-1
    current_memory_utilization: float = 0.0  # 0-1

@dataclass
class SliceMetadata:
    """Slice metadata for placement decisions."""

    slice_id: str
    start_layer: int
    end_layer: int

    # Size characteristics
    parameter_count: int = 0
    activation_size_bytes: int = 0
    estimated_flops_per_token: float = 0.0

    # Device hints
    preferred_device_type: Optional[str] = None
    min_memory_bytes: int = 0

    # Policy tags
    is_private: bool = False
    latency_sensitive: bool = False

class CostModel:
    """
    Computes cost estimates for slice placement decisions.

    Cost factors:
    - Compute cost: FLOPS / device capability
    - Memory cost: size / available memory
    - Network cost: bandwidth requirements / network capacity
    - Latency cost: estimated execution time
    """

    def __init__(self):
        self._lock = threading.Lock()

    def compute_compute_cost(
        self, slice_metadata: SliceMetadata, worker_profile: WorkerProfile
    ) -> float:
        """
        Compute normalized compute cost for placing slice on worker.

        Returns lower value = better fit
        """
        if worker_profile.device_type == "gpu":
            device_flops = worker_profile.gpu_flops_tflops * 1e12  # Convert to FLOPS
        else:
            # CPU estimate (rough)
            device_flops = worker_profile.cpu_cores * 30e9  # ~30 GFLOPS per core

        compute_cost = slice_metadata.estimated_flops_per_token / device_flops

        return compute_cost

    def compute_memory_cost(
        self, slice_metadata: SliceMetadata, worker_profile: WorkerProfile
    ) -> float:
        """
        Compute normalized memory cost for placing slice on worker.

        Returns lower value = better fit
        """
        if worker_profile.memory_free <= 0:
            return float("inf")

        memory_cost = slice_metadata.activation_size_bytes / worker_profile.memory_free

        return memory_cost

    def compute_network_cost(
        self,
        slice_metadata: SliceMetadata,
        source_worker: WorkerProfile,
        target_worker: WorkerProfile,
    ) -> float:
        """
        Compute normalized network cost for transferring slice.

        Returns lower value = better fit (faster transfer)
        """
        if (
            source_worker.network_bandwidth_gbps <= 0
            or target_worker.network_bandwidth_gbps <= 0
        ):
            return float("inf")

        bandwidth_bytes_per_sec = (
            (
                source_worker.network_bandwidth_gbps
                + target_worker.network_bandwidth_gbps
            )
            / 2
            * 1e9
        )

        network_cost = (
            slice_metadata.parameter_count * 4 / bandwidth_bytes_per_sec
        )  # bytes per sec

        return network_cost

    def estimate_latency(
        self,
        slice_metadata: SliceMetadata,
        worker_profile: WorkerProfile,
        network_latency_ms: float = 0.1,
    ) -> float:
        """
        Estimate total latency for executing slice on worker.

        Includes: network transfer + compute time
        """
        # Network latency (if not colocated)
        network_cost_ms = 0.0
        if network_latency_ms > 0:
            bandwidth_bytes_per_sec = worker_profile.network_bandwidth_gbps * 1e9
            network_cost_ms = (
                slice_metadata.parameter_count * 4 / bandwidth_bytes_per_sec * 1000
            )

        # Compute latency estimate
        if worker_profile.device_type == "gpu":
            compute_latency_ms = (
                slice_metadata.estimated_flops_per_token
                / (worker_profile.gpu_flops_tflops * 1e12)
            ) * 1000
        else:
            compute_latency_ms = (
                slice_metadata.estimated_flops_per_token
                / (worker_profile.cpu_cores * 30e9)
            ) * 1000

        return network_cost_ms + compute_latency_ms

class Scheduler:
    """
    Cost-aware scheduler for slice placement decisions.

    Features:
    - Greedy best-fit placement
    - Load balancing across workers
    - Device type preferences (GPU for compute-heavy layers)
    - Memory-aware placement
    - Network topology awareness
    """

    def __init__(self, worker_profiles: List[WorkerProfile]):
        self.workers = worker_profiles
        self.cost_model = CostModel()

        # Track current slice placements
        self._slice_placements: Dict[str, str] = {}  # slice_id -> worker_url

        # Lock for thread safety
        self._lock = threading.Lock()

    def build_worker_inventory(self) -> Dict[str, WorkerProfile]:
        """Build worker inventory from profiles."""
        return {w.url: w for w in self.workers}

    def select_best_worker(
        self, slice_metadata: SliceMetadata
    ) -> Optional[WorkerProfile]:
        """
        Select best worker for given slice using cost model.

        Returns worker profile with lowest total cost, or None if no suitable worker.
        """
        inventory = self.build_worker_inventory()

        # Filter healthy workers
        candidates = [w for w in self.workers if w.is_healthy]

        if not candidates:
            return None

        best_worker = None
        min_cost = float("inf")

        for worker in candidates:
            # Skip if memory insufficient
            if slice_metadata.activation_size_bytes > worker.memory_free:
                continue

            # Skip if GPU requested but unavailable
            if (
                slice_metadata.preferred_device_type == "gpu"
                and worker.device_type != "gpu"
            ):
                continue

            # Compute total cost
            compute_cost = self.cost_model.compute_compute_cost(slice_metadata, worker)
            memory_cost = self.cost_model.compute_memory_cost(slice_metadata, worker)
            network_cost = 0.0  # Assuming colocated for simplicity

            total_cost = compute_cost + memory_cost + network_cost

            if total_cost < min_cost:
                min_cost = total_cost
                best_worker = worker

        return best_worker

    def assign_slice(self, slice_metadata: SliceMetadata) -> Optional[str]:
        """
        Assign slice to best available worker.

        Returns worker URL or None if assignment fails.
        """
        with self._lock:
            best_worker = self.select_best_worker(slice_metadata)

            if best_worker is None:
                return None

            # Record placement
            self._slice_placements[slice_metadata.slice_id] = best_worker.url

            return best_worker.url

    def get_placement_plan(
        self, slices: List[Tuple[int, int, SliceMetadata]]
    ) -> Dict[str, str]:
        """
        Get placement plan for all slices.

        Returns mapping of slice_id -> worker_url
        """
        placements = {}

        # Sort slices by size (largest first) for better packing
        sorted_slices = sorted(
            slices, key=lambda s: s[2].activation_size_bytes, reverse=True
        )

        for start, end, metadata in sorted_slices:
            worker_url = self.assign_slice(metadata)

            if worker_url is not None:
                placements[f"slice_{start}_{end}"] = worker_url

        return placements

    def rebalance_load(self) -> Optional[WorkerProfile]:
        """
        Identify most loaded worker and suggest moving slices to less loaded workers.

        Returns overloaded worker profile or None if balanced.
        """
        inventory = self.build_worker_inventory()

        # Calculate load score for each worker
        worker_scores = []
        for worker in self.workers:
            if not worker.is_healthy:
                continue

            # Load score based on utilization and memory pressure
            utilization_score = (
                0.4 * worker.current_gpu_utilization
                + 0.3 * worker.current_cpu_utilization
                + 0.3 * worker.current_memory_utilization
            )

            worker_scores.append((worker, utilization_score))

        # Sort by score descending
        worker_scores.sort(key=lambda x: x[1], reverse=True)

        # Identify overloaded worker (>70% load)
        if worker_scores and worker_scores[0][1] > 0.7:
            return worker_scores[0][0]

        return None

    def get_placement_statistics(self) -> Dict[str, Any]:
        """Get placement statistics."""
        inventory = self.build_worker_inventory()

        # Count slices per worker
        placements_per_worker = {}
        for slice_id, worker_url in self._slice_placements.items():
            placements_per_worker[worker_url] = (
                placements_per_worker.get(worker_url, 0) + 1
            )

        total_slices = len(self._slice_placements)

        return {
            "total_slices": total_slices,
            "placements_per_worker": placements_per_worker,
            "workers_with_slices": sum(
                1 for p in placements_per_worker.values() if p > 0
            ),
            "utilization_by_worker": {
                w.url: {
                    "gpu_utilization": w.current_gpu_utilization,
                    "cpu_utilization": w.current_cpu_utilization,
                    "memory_utilization": w.current_memory_utilization,
                }
                for w in self.workers
                if w.is_healthy
            },
        }

class TopologyAwareScheduler(Scheduler):
    """
    Scheduler with network topology awareness.

    Considers:
    - Physical distance between devices
    - Network path quality
    - Shared memory pools (NUMA)
    """

    def __init__(
        self,
        worker_profiles: List[WorkerProfile],
        topology: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(worker_profiles)
        self.topology = topology or {}

        # Build adjacency matrix for network latency
        self._network_latencies: Dict[Tuple[str, str], float] = {}

    def update_network_latency(self, w1_url: str, w2_url: str, latency_ms: float):
        """Update measured network latency between workers."""
        self._network_latencies[(w1_url, w2_url)] = latency_ms
        self._network_latencies[(w2_url, w1_url)] = latency_ms

    def compute_network_cost_with_topology(
        self,
        slice_metadata: SliceMetadata,
        source_worker: WorkerProfile,
        target_worker: WorkerProfile,
    ) -> float:
        """
        Compute network cost considering topology.

        Uses measured latencies when available, estimates otherwise.
        """
        # Check for direct connection
        if (source_worker.url, target_worker.url) in self._network_latencies:
            latency_ms = self._network_latencies[(source_worker.url, target_worker.url)]
            bandwidth_bytes_per_sec = (
                (
                    source_worker.network_bandwidth_gbps
                    + target_worker.network_bandwidth_gbps
                )
                / 2
                * 1e9
            )

            network_cost = (
                slice_metadata.parameter_count * 4 / bandwidth_bytes_per_sec * 1000
            )

        elif source_worker.url == target_worker.url:
            # Same worker, no network cost
            return 0.0

        else:
            # Estimate based on physical distance if available
            w1_location = self.topology.get(source_worker.url, {}).get("location", "")
            w2_location = self.topology.get(target_worker.url, {}).get("location", "")

            # Rough estimate: 10ms per km for fiber (very conservative)
            location1 = getattr(source_worker, "_location", "")
            location2 = getattr(target_worker, "_location", "")

            if location1 and location2:
                # Extract numeric part from location string like "rack-3" or "pod-2"
                import re

                num1 = (
                    int(re.search(r"\d+", location1).group())
                    if re.search(r"\d+", location1)
                    else 0
                )
                num2 = (
                    int(re.search(r"\d+", location2).group())
                    if re.search(r"\d+", location2)
                    else 0
                )

                distance_km = (
                    abs(num1 - num2) * 10
                )  # Rough estimate: 10km per rack difference
                latency_ms = distance_km * 0.1  # 10ms per km

                bandwidth_bytes_per_sec = (
                    (
                        source_worker.network_bandwidth_gbps
                        + target_worker.network_bandwidth_gbps
                    )
                    / 2
                    * 1e9
                )

                network_cost = (
                    slice_metadata.parameter_count * 4 / bandwidth_bytes_per_sec * 1000
                )

            else:
                # Default estimate
                latency_ms = 1.0  # Assume 1ms local network
                bandwidth_bytes_per_sec = source_worker.network_bandwidth_gbps * 1e9

                network_cost = (
                    slice_metadata.parameter_count * 4 / bandwidth_bytes_per_sec * 1000
                )

        return network_cost

if __name__ == "__main__":
    # Demo scheduler

    # Create worker profiles
    workers = [
        WorkerProfile(
            url="http://worker-gpu-1:8003",
            device_type="gpu",
            gpu_model="NVIDIA_A100_80GB",
            memory_total=80 * 1024**3,
            memory_free=60 * 1024**3,
            cpu_cores=96,
            gpu_flops_tflops=2000,  # A100 FP16 TFLOPS
            network_interface="eth0",
            network_bandwidth_gbps=25.0,
        ),
        WorkerProfile(
            url="http://worker-cpu-1:8003",
            device_type="cpu",
            memory_total=128 * 1024**3,
            memory_free=100 * 1024**3,
            cpu_cores=64,
            network_interface="eth0",
            network_bandwidth_gbps=10.0,
        ),
    ]

    # Create slices
    slices = [
        SliceMetadata(
            slice_id="slice_0_2",
            start_layer=0,
            end_layer=2,
            parameter_count=100000,
            activation_size_bytes=50000,
            estimated_flops_per_token=1e9,
            preferred_device_type="gpu",
        ),
        SliceMetadata(
            slice_id="slice_2_3",
            start_layer=2,
            end_layer=3,
            parameter_count=50000,
            activation_size_bytes=25000,
            estimated_flops_per_token=5e8,
        ),
    ]

    # Create scheduler
    scheduler = Scheduler(workers)

    # Get placement plan
    placements = scheduler.get_placement_plan(slices)

    print("Placement Plan:")
    for slice_id, worker_url in placements.items():
        print(f"  {slice_id} -> {worker_url}")
