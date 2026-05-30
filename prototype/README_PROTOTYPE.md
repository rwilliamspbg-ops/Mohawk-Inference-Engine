Prototype demo

This prototype demonstrates a minimal multi-device layer-splitting demo using a toy model. It simulates two workers (FastAPI) that accept slice preload and execution.

Quickstart:

1. Install dependencies:

```bash
python -m pip install -r prototype/requirements.txt
```

2. Start two workers in separate terminals:

```bash
python prototype/worker.py --port 8001
python prototype/worker.py --port 8002
```

3. Run the demo:

```bash
python prototype/run_demo.py
```

Notes:
- This is a functional prototype illustrating partitioning, preload, and remote execution. It uses pickle-serialized weights and inputs for simplicity.
- PQC and secure transport are not implemented in this demo; the architecture doc outlines where PQC would integrate. The code is organized so an AEAD layer can be added to the transport easily.
