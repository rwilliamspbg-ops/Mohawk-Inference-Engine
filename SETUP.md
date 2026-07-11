# Mohawk Inference Engine - Setup Guide

## Setup Options

## 1) One-Click Launcher (recommended)

```bash
./launch.sh
```

What it does:
- Creates/uses local virtual environment
- Installs missing dependencies
- Offers native and Docker full-stack launch modes
- Auto-launches desktop GUI when environment supports it

## 2) Docker Full Stack

```bash
docker compose up -d --build
```

Services:
- GUI backend: `http://localhost:8003`
- Worker: `http://localhost:8004`

Desktop GUI container behavior:
- Starts when display is available
- Exits cleanly if `DISPLAY` is missing

Skip desktop GUI container explicitly:

```bash
MOHAWK_SKIP_DESKTOP_GUI=1 docker compose up -d --build
```

## 3) Native Backend + GUI

```bash
source .venv/bin/activate
python launch.py
```

Or run API services manually:

```bash
python -m uvicorn prototype.worker:app --host 127.0.0.1 --port 8004
python -m uvicorn prototype.gui_backend:app --host 127.0.0.1 --port 8003
```

## Health Checks

```bash
curl http://localhost:8003/health
curl http://localhost:8004/health
```

## Functional Validation

Run end-to-end checks for model selection and chat inference:

```bash
python test_user_functions.py
```

Expected summary:

```text
SUMMARY: 33/33 passed (100.0%)
```

## Troubleshooting

- If GUI does not open in Docker mode, verify `DISPLAY` and X11 access.
- If ports are busy (`8003`, `8004`), stop conflicting processes before launch.
- If `docker` is unavailable in devcontainer, rebuild container to apply `.devcontainer/devcontainer.json` features.
