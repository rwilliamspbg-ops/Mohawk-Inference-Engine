# Mohawk Inference Engine - Install Guide

## Prerequisites

- Python 3.10+
- Git
- Docker + Docker Compose (recommended for full stack)
- Linux/macOS shell or PowerShell on Windows

For desktop GUI launch on Linux, ensure display libraries and `DISPLAY` are available.

## Clone

```bash
git clone https://github.com/rwilliamspbg-ops/Mohawk-Inference-Engine.git
cd Mohawk-Inference-Engine
```

## Python Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

## Optional: Devcontainer

In VS Code:
- Dev Containers: Rebuild and Reopen in Container

Then run:

```bash
bash .devcontainer/post_create.sh
```

Fast smoke mode:

```bash
MOHAWK_SKIP_LIBOQS_BUILD=1 MOHAWK_SKIP_PY_DEPS=1 bash .devcontainer/post_create.sh
```

## Verify Install

```bash
python - <<'PY'
import fastapi, uvicorn, requests, psutil
print('Core dependencies OK')
PY
```

## Next

- Go to `SETUP.md` for runtime startup options.
- Go to `QUICKSTART.md` for API smoke tests.
