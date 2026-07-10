import inspect
import time
from functools import wraps

class Telemetry:
    def __init__(self, metrics_dict, lock):
        self.metrics = metrics_dict
        self.lock = lock
        # histogram bucket boundaries in seconds
        self.buckets = [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]

    def record(self, name_sum, name_count, duration):
        # record sum and count in metrics dict
        with self.lock:
            self.metrics[name_sum] = self.metrics.get(name_sum, 0.0) + duration
            self.metrics[name_count] = self.metrics.get(name_count, 0) + 1
            # also update histogram buckets for this metric prefix
            try:
                base = name_sum
                if base.endswith("_sum"):
                    base = base[:-4]
                hist_prefix = f"{base}_hist"
                # find the appropriate bucket
                for b in self.buckets:
                    key = f"{hist_prefix}_{b}"
                    if duration <= b:
                        self.metrics[key] = self.metrics.get(key, 0) + 1
                        break
                else:
                    # overflow bucket
                    key = f"{hist_prefix}_+Inf"
                    self.metrics[key] = self.metrics.get(key, 0) + 1
            except Exception:
                pass

    def timed(self, name_sum, name_count):
        def decorator(func):
            if inspect.iscoroutinefunction(func):

                async def async_wrapper(*args, **kwargs):
                    t0 = time.time()
                    try:
                        return await func(*args, **kwargs)
                    finally:
                        dt = time.time() - t0
                        self.record(name_sum, name_count, dt)

                wraps(func)(async_wrapper)
                return async_wrapper
            else:

                def sync_wrapper(*args, **kwargs):
                    t0 = time.time()
                    try:
                        return func(*args, **kwargs)
                    finally:
                        dt = time.time() - t0
                        self.record(name_sum, name_count, dt)

                wraps(func)(sync_wrapper)
                return sync_wrapper

        return decorator
