Prototype demo

This prototype demonstrates a minimal multi-device layer-splitting demo using a toy model. It simulates two workers (FastAPI) that accept slice preload and execution.

Quickstart:

1. Install dependencies:

```bash
python -m pip install -r prototype/requirements.txt
```

2. Start two workers in separate terminals (secure worker available):

```bash
# insecure worker (no encryption)
python prototype/worker.py --port 8001
# secure worker (handshake + AEAD) listens on a separate port
python prototype/worker_secure.py --port 8003
```

3. Run the demo:

```bash
python prototype/run_demo.py
```

Notes:
- This is a functional prototype illustrating partitioning, preload, and remote execution. It uses pickle-serialized weights and inputs for simplicity.
-- A secure path using X25519 + optional liboqs hybrid KEM is scaffolded in `prototype/crypto.py` and `prototype/worker_secure.py`. To enable full hybrid PQC tests, install liboqs / pyOQS in the environment (see `docs/PQC_INTEGRATION.md`).
