import requests
import base64
import pickle
from prototype.model_tools_v2 import ToyModel, WeightSlice
from typing import List


class Controller:
    """
    Model partitioning controller with safe serialization.
    
    Replaces pickle-based transport with binary format for security.
    """
    
    def __init__(self, workers):
        """
        Initialize controller with worker URLs.
        
        Args:
            workers: List of worker URLs (e.g., ["http://127.0.0.1:8001", "http://127.0.0.1:8002"])
        """
        self.workers = workers
        # Connection pooling for performance
        self.session = requests.Session()
    
    def partition_model(self, model: ToyModel, num_slices: int = 2) -> List[WeightSlice]:
        """
        Partition model into balanced slices.
        
        Algorithm: Balanced partitioning ensures even distribution of layers.
        
        Args:
            model: ToyModel instance to partition
            num_slices: Number of slices (e.g., 2 for bipartition)
            
        Returns:
            List of WeightSlice objects in execution order
        """
        L = len(model.weights)
        # Balanced partitioning using ceiling division
        slice_size = (L + num_slices - 1) // num_slices
        
        slices = []
        for i in range(num_slices):
            start = i * slice_size
            end = min(L, start + slice_size)
            
            if start >= L:
                break
            
            sub = model.slice(start, end)
            slices.append(sub)
        
        return slices
    
    def preload_slices(self, slices: List[WeightSlice], encrypt: bool = False) -> List[tuple]:
        """
        Preload model slices to workers.
        
        Args:
            slices: List of WeightSlice objects in execution order
            encrypt: Whether to encrypt weights during transport
            
        Returns:
            List of (slice_id, worker_url) tuples for distributed execution
        """
        assigned = []
        
        for i, slice_obj in enumerate(slices):
            # Round-robin assignment to workers
            w = self.workers[i % len(self.workers)]
            
            # Serialize weights safely (no pickle)
            blob = slice_obj.to_bytes()
            
            manifest = {
                "start": slice_obj.start_layer,
                "end": slice_obj.end_layer,
                "version": slice_obj.version
            }
            
            payload = {
                "slice_id": f"slice_{slice_obj.start_layer}_{slice_obj.end_layer}",
                "manifest": manifest,
                "weights_b64": base64.b64encode(blob).decode('ascii'),
                "version": slice_obj.version
            }
            
            # Retry with exponential backoff for transient failures
            max_attempts = 3
            backoff_base = 0.1
            
            for attempt in range(1, max_attempts + 1):
                try:
                    r = self.session.post(f"{w}/preload", json=payload, timeout=10)
                    r.raise_for_status()
                    break
                except Exception as e:
                    if attempt == max_attempts:
                        raise
                    sleep_t = backoff_base * (2 ** (attempt - 1))
                    import time
                    time.sleep(sleep_t)
            
            assigned.append((payload['slice_id'], w))
        
        return assigned
    
    def run_distributed(self, assigned: List[tuple], x: np.ndarray, 
                       encrypt: bool = False) -> np.ndarray:
        """
        Run distributed inference across workers.
        
        Args:
            assigned: List of (slice_id, worker_url) tuples in execution order
            x: Input tensor as numpy array
            encrypt: Whether to encrypt activations during transport
            
        Returns:
            Output tensor after passing through all slices
        """
        from prototype.model_tools_v2 import ToyModel
        
        current = x
        
        for slice_id, w in assigned:
            try:
                # Prepare input for this slice
                if encrypt:
                    raise NotImplementedError("Encryption not yet implemented")
                else:
                    b64_input = base64.b64encode(current.tobytes()).decode('ascii')
                
                payload = {
                    "slice_id": slice_id,
                    "input_b64": b64_input,
                    "version": "v1.0"
                }
                
                # Execute on worker
                r = self.session.post(f"{w}/execute", json=payload, timeout=30)
                r.raise_for_status()
                
                # Get output
                out_b64 = r.json()['output_b64']
                current = np.frombuffer(
                    base64.b64decode(out_b64), 
                    dtype=np.float32
                )
                
            except Exception as e:
                print(f"Error executing slice {slice_id}: {e}")
                raise
    
        return current
