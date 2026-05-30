# Getting Started

This guide covers the shortest path from a fresh clone to running the prototype locally.

## Prerequisites

- Python 3.12 or newer
- `pip`
- Optional: a native liboqs install if you want the hybrid PQC path to activate

## Install Dependencies

```bash
python -m pip install -r prototype/requirements.txt
```

If you have a local liboqs install, export:

```bash
export OQS_INSTALL_PATH=/usr/local
```

## Run the Demo

```bash
python prototype/run_demo.py
```

That script compares a single-node baseline against the distributed toy model path.

## Run the Secure Worker

```bash
python prototype/worker_secure.py --port 8003
```

The secure path uses the hybrid X25519 + OQS adapter when the binding is present.

## Run Tests

```bash
python -m pytest -q prototype/test_oqs_hybrid.py prototype/test_secure_hybrid_integration.py prototype/test_concurrency_smoke.py prototype/test_secure_run.py -q -rA
```

## Useful Docs

- [README](../README.md)
- [Architecture](ARCHITECTURE.md)
- [PQC integration](PQC_INTEGRATION.md)
- [Contributing](../CONTRIBUTING.md)