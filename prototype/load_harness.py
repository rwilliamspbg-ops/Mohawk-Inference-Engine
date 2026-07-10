import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np

from prototype.model_tools import ToyModel
from prototype.session_manager import SessionManager

def run_session_sync(sm: SessionManager, model, session_idx, encrypt=False):
    sid = sm.start_session(model, num_slices=2, encrypt=encrypt)
    x = np.random.default_rng(session_idx).standard_normal((8, 1)).astype("float32")
    out = sm.infer(sid, x)
    sm.end_session(sid)
    return out

def run_load(workers, concurrency=20, total=100, encrypt=False):
    sm = SessionManager(workers)
    model = ToyModel([8, 16, 16, 8], seed=42)
    results = []
    start = time.time()
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [
            ex.submit(run_session_sync, sm, model, i, encrypt) for i in range(total)
        ]
        for f in as_completed(futures):
            results.append(f.result())
    end = time.time()
    print(f"Completed {total} sessions in {end-start:.2f}s")
    return results

if __name__ == "__main__":
    workers = ["http://127.0.0.1:8003", "http://127.0.0.1:8003"]
    import json

    import requests

    runs = [
        {"concurrency": 50, "total": 200},
        {"concurrency": 100, "total": 500},
        {"concurrency": 200, "total": 1000},
    ]
    all_agg = {}
    for rconf in runs:
        c = rconf["concurrency"]
        t = rconf["total"]
        print(f"Starting run total={t} concurrency={c}")
        run_load(workers, concurrency=c, total=t, encrypt=True)
        # fetch metrics from workers
        agg = {}
        for w in set(workers):
            try:
                resp = requests.get(f"{w}/metrics", timeout=5)
                resp.raise_for_status()
                m = resp.json()
                print(f"metrics from {w}: {m}")
                for k, v in m.items():
                    agg[k] = agg.get(k, 0) + v
            except Exception as e:
                print(f"failed to fetch metrics from {w}: {e}")
        print(f"aggregated metrics for run {t}: {agg}")
        all_agg[f"run_{t}"] = agg
        # persist a copy
        try:
            with open(f"/tmp/metrics_run_{t}.json", "w") as fh:
                json.dump(agg, fh)
        except Exception as e:
            print(f"failed to write metrics file: {e}")
    print(f"all runs aggregated: {all_agg}")
