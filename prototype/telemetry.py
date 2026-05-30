import time
import inspect
from functools import wraps


class Telemetry:
    def __init__(self, metrics_dict, lock):
        self.metrics = metrics_dict
        self.lock = lock

    def record(self, name_sum, name_count, duration):
        # record sum and count in metrics dict
        with self.lock:
            self.metrics[name_sum] = self.metrics.get(name_sum, 0.0) + duration
            self.metrics[name_count] = self.metrics.get(name_count, 0) + 1

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
