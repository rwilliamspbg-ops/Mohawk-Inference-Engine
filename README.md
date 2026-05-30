# Mohawk Inference Engine

Mohawk Inference Engine is a local inference and management stack for splitting model execution across multiple devices while keeping transport and session handling secure. The project focuses on three capabilities that are hard to get in one place in lightweight desktop tools: multi-device layer splitting, PQC-secured edge offload, and high-concurrency session management.

## What This Repo Contains

- A toy layer-splitting runtime that partitions a model into slices and runs them across workers.
- A secure controller/worker path with X25519 plus optional liboqs-backed hybrid KEM support.
- A session manager and load harness for concurrent encrypted inference runs.
- Telemetry and timing hooks for preload and execute paths.

## Quick Start

```bash
python -m pip install -r prototype/requirements.txt
python prototype/run_demo.py
```

For the secure prototype, start the secure worker in a separate terminal:

```bash
python prototype/worker_secure.py --port 8003
```

If you have a local liboqs install, set:

```bash
export OQS_INSTALL_PATH=/usr/local
```

## Recommended Reading

- [Project scope](docs/SCOPE.md)
- [Architecture spec](docs/ARCHITECTURE.md)
- [PQC integration notes](docs/PQC_INTEGRATION.md)
- [Getting started guide](docs/GETTING_STARTED.md)
- [Contributor guide](CONTRIBUTING.md)

## Testing

Run the focused prototype checks with:

```bash
python -m pytest -q prototype/test_oqs_hybrid.py prototype/test_secure_hybrid_integration.py prototype/test_concurrency_smoke.py prototype/test_secure_run.py -q -rA
```

## Release Notes

- Release `v0.1.0` includes the liboqs devcontainer, secure prototype path, telemetry, and the scaling harness.
- The repository is licensed under Apache-2.0. See [LICENSE](LICENSE).
