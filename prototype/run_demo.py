import numpy as np
import pickle
import base64
import time
from prototype.model_tools import ToyModel
from prototype.controller import Controller

# config
worker_urls = ["http://127.0.0.1:8001", "http://127.0.0.1:8002"]

def single_node_run(model, x):
    return model.forward(x)

def distributed_run(model, x):
    c = Controller(worker_urls)
    slices = c.partition_model(model, num_slices=2)
    assigned = c.preload_slices(slices)
    x_blob = pickle.dumps(x)
    out_blob = c.run_distributed(assigned, x_blob)
    out = pickle.loads(out_blob)
    return out

if __name__ == '__main__':
    # build model
    model = ToyModel([8,16,16,8], seed=42)
    x = np.random.default_rng(1).standard_normal((8,1)).astype('float32')

    print("Running single-node baseline...")
    baseline = single_node_run(model, x)

    print("Running distributed demo (requires two workers at :8001 and :8002)...")
    t0 = time.time()
    out = distributed_run(model, x)
    t1 = time.time()
    print(f"Distributed run time: {t1-t0:.3f}s")

    # compare
    diff = np.max(np.abs(baseline - out))
    print(f"Max abs diff vs baseline: {diff}")
    if diff < 1e-5:
        print("SUCCESS: outputs match within tolerance")
    else:
        print("WARNING: outputs differ — check serialization/ordering")
