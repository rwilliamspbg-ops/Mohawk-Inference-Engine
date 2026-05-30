import requests
import base64
import pickle
from prototype.model_tools import ToyModel

class Controller:
    def __init__(self, workers):
        # workers: list of urls
        self.workers = workers

    def partition_model(self, model: ToyModel, num_slices=2):
        L = len(model.weights)
        per = max(1, L // num_slices)
        slices = []
        for i in range(0, L, per):
            start = i
            end = min(L, i+per)
            sub = model.slice(start, end)
            slices.append((start, end, sub))
        return slices

    def preload_slices(self, slices):
        # round-robin assign to workers
        assigned = []
        for i, (start,end,sub) in enumerate(slices):
            w = self.workers[i % len(self.workers)]
            blob = sub.serialize()
            b64 = base64.b64encode(blob).decode('ascii')
            manifest = {"start": start, "end": end}
            payload = {"slice_id": f"slice_{start}_{end}", "manifest": manifest, "weights_b64": b64}
            r = requests.post(f"{w}/preload", json=payload, timeout=10)
            r.raise_for_status()
            assigned.append((payload['slice_id'], w))
        return assigned

    def run_distributed(self, assigned, x_blob):
        # assigned: list of (slice_id, worker_url) in order
        current = x_blob
        for slice_id, w in assigned:
            b64 = base64.b64encode(current).decode('ascii')
            payload = {"slice_id": slice_id, "input_b64": b64}
            r = requests.post(f"{w}/execute", json=payload, timeout=30)
            r.raise_for_status()
            out_b64 = r.json()['output_b64']
            current = base64.b64decode(out_b64)
        return current
