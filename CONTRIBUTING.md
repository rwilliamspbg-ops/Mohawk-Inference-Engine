# Contributing to Mohawk Inference Engine

Thanks for helping improve Mohawk Inference Engine. This repository is intentionally small, but it has a few conventions that keep the prototype and release docs easy to follow.

## Before You Start

- Read [README.md](README.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), and [docs/PQC_INTEGRATION.md](docs/PQC_INTEGRATION.md).
- If you are touching secure transport or session logic, run the focused prototype tests before opening a PR.
- Keep changes small and scoped. This repo favors incremental updates over broad rewrites.

## Development Setup

```bash
python -m pip install -r prototype/requirements.txt
```

Optional secure-local setup:

```bash
export OQS_INSTALL_PATH=/usr/local
```

## Code Style

- Prefer readable, explicit Python over clever abstractions.
- Preserve the current module structure under `prototype/`.
- Keep doc updates in sync with code changes.
- Avoid adding extra dependencies unless they clearly reduce complexity or improve correctness.

## Testing Expectations

Run the relevant tests for the slice you changed:

```bash
python -m pytest -q prototype/test_oqs_hybrid.py prototype/test_secure_hybrid_integration.py prototype/test_concurrency_smoke.py prototype/test_secure_run.py -q -rA
```

If you modify the load harness or telemetry path, also run the broader prototype smoke flow with the secure worker.

## Pull Requests

- Use a short imperative commit message.
- Include a note about any environment variables or native libraries required to reproduce the change.
- Mention any tests you ran in the PR description.

## Release Hygiene

- Do not commit generated artifacts, virtual environments, or local caches.
- If you update the secure flow or binding assumptions, document the runtime requirement in [docs/PQC_INTEGRATION.md](docs/PQC_INTEGRATION.md).