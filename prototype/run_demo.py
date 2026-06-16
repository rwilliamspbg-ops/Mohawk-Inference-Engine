import numpy as np

from prototype.controller import Controller
from prototype.model_tools import ToyModel, WeightSlice


def single_node_run(model, x):
    """Baseline: run model on single node (all layers)."""
    return model.forward(x)


def distributed_run(model, x):
    """
    Run model distributed across workers.

    Uses safe binary serialization (no pickle) for security.
    """
    c = Controller(["http://127.0.0.1:8001", "http://127.0.0.1:8002"])
    slices = c.partition_model(model, num_slices=2)
    assigned = c.preload_slices(slices)

    x_flat = np.ravel(x).tobytes()
    out_bytes = c.run_distributed(assigned, x_flat)
    out = np.frombuffer(out_bytes, dtype=np.float32)

    return out


if __name__ == "__main__":
    # Build model
    model = ToyModel([8, 16, 16, 8], seed=42)
    x = np.random.default_rng(1).standard_normal((8, 1)).astype("float32")

    print("Running single-node baseline...")
    baseline = single_node_run(model, x)

    print("Running distributed demo (requires two workers at :8001 and :8002)...")
    try:
        t0 = __import__("time").time()
        out = distributed_run(model, x)
        t1 = __import__("time").time()
        print(f"Distributed run time: {t1-t0:.3f}s")

        # Compare outputs (reshape for comparison)
        baseline_reshaped = baseline.reshape(-1, 8)
        out_reshaped = out.reshape(-1, 8) if len(out.shape) > 1 else out.reshape(1, -1)

        diff = np.max(np.abs(baseline_reshaped.flatten() - out_reshaped.flatten()))
        print(f"Max abs diff vs baseline: {diff}")

        if diff < 1e-5:
            print("SUCCESS: outputs match within tolerance")
        else:
            print("WARNING: outputs differ — check serialization/ordering")
    except Exception as e:
        print(f"Distributed run failed (expected if workers not running): {e}")
        print("This is normal when testing without workers started.")
