# Mohawk Inference Engine - Setup & Runtime Guide

## Architecture Overview

```
Your Machine (Local Development)
├── PyQt6 GUI (Desktop Application)
│   └── Connects to backend services at localhost:8003 and localhost:8004
│
└── Docker Containers (Backend Services)
    ├── mohawk-gui container (port 8003)
    │   └── Runs health checks and service endpoints
    ├── mohawk-worker container (port 8004)
    │   └── Runs inference worker backend
    └── mohawk-network (Docker network for inter-container communication)
```

## Prerequisites

- **Docker Desktop** (Windows/Mac) or **Docker Engine + Docker Compose** (Linux)
- **Python 3.12+** installed locally
- **PyQt6 and dependencies** installed locally

## Installation & Setup

### 1. Install Local Dependencies

The GUI runs locally and requires PyQt6 and system libraries:

```bash
# Install Python dependencies
pip install -r requirements.txt

# Verify PyQt6 installation
python -c "from PyQt6.QtWidgets import QApplication; print('PyQt6 OK')"
```

### 2. Start Docker Containers

The backend services run in Docker:

```bash
# Start containers in background
docker compose up -d

# Verify containers are running and healthy
docker ps

# Expected output:
# - mohawk-gui: status "Up X seconds (healthy)"
# - mohawk-worker: status "Up X seconds (healthy)"
```

### 3. Run the GUI Locally

After containers are running, launch the GUI on your machine:

```bash
# From the project root directory
python mohawk_gui/main.py

# Or with custom settings:
python mohawk_gui/main.py --host localhost --port 8003 --ssl-enabled
```

The GUI window will open and connect to the Docker-based backend services.

## Services & Ports

| Service | Port | Location | Purpose |
|---------|------|----------|---------|
| mohawk-gui | 8003 | Docker Container | Backend API & health endpoints |
| mohawk-worker | 8004 | Docker Container | Inference worker service |
| mohawk-desktop-gui | n/a | Docker Container | Desktop GUI launcher (display-dependent) |
| PyQt6 GUI | (Local) | Your Machine | Desktop application interface |

## Desktop GUI Launch Behavior

- `docker compose up -d --build` includes `mohawk-desktop-gui` for one-click full-stack startup.
- If `DISPLAY` is not set, the desktop GUI service exits cleanly and backend APIs continue running.
- `launch.py` sets `MOHAWK_SKIP_DESKTOP_GUI=1` when orchestrating compose to avoid duplicate GUI instances, then launches host desktop GUI directly when supported.

Skip container desktop GUI explicitly:

```bash
MOHAWK_SKIP_DESKTOP_GUI=1 docker compose up -d --build
```

## Container Management

### View Container Logs

```bash
# GUI service logs
docker logs mohawk-gui -f

# Worker service logs
docker logs mohawk-worker -f

# Follow both simultaneously
docker compose logs -f
```

### Stop Containers

```bash
# Stop gracefully
docker compose stop

# Stop and remove containers
docker compose down

# Stop and remove all data (volumes)
docker compose down -v
```

### Restart Services

```bash
# Restart specific container
docker restart mohawk-gui
docker restart mohawk-worker

# Restart all containers
docker compose restart
```

### Check Container Health

```bash
# Inspect container details
docker inspect mohawk-gui
docker inspect mohawk-worker

# View port mappings
docker port mohawk-gui
docker port mohawk-worker
```

## Troubleshooting

### Containers Won't Start

```bash
# Check for port conflicts
docker ps -a

# If port 8003 or 8004 already in use:
docker compose down
# Then identify and stop the conflicting service
```

### GUI Can't Connect to Backend

Ensure:
1. Containers are running: `docker ps` shows both containers with "Up" status
2. Containers are healthy: Check "healthy" in the STATUS column
3. Port mappings are correct:
   - `docker port mohawk-gui` should show `8003/tcp -> 0.0.0.0:8003`
   - `docker port mohawk-worker` should show `8003/tcp -> 0.0.0.0:8004`

### PyQt6 Import Errors on Linux/Mac

If you see import errors, install system dependencies:

**Ubuntu/Debian:**
```bash
sudo apt-get install python3-pyqt6 libxkbcommon-x11-0 libdbus-1-3 libgl1
```

**macOS:**
```bash
brew install pyqt6
```

**macOS (if brew fails):**
```bash
pip install --upgrade PyQt6
```

### Memory/Performance Issues

Monitor container resource usage:

```bash
# Real-time stats
docker stats

# View specific container memory usage
docker stats mohawk-gui --no-stream
docker stats mohawk-worker --no-stream
```

If containers consume too much memory, rebuild with smaller base images or adjust volume mounts.

## Development Workflow

### Running Tests

```bash
# Run tests inside a container
docker exec mohawk-gui python -m pytest mohawk_gui/tests/

# Or run locally (if tests installed)
pytest tests/ -v
```

### Viewing Model Files

```bash
# List models in container volume
docker exec mohawk-worker ls /app/models/

# Copy a model from container to local
docker cp mohawk-worker:/app/models/model.bin ./models/
```

### Debugging with Container Shell

```bash
# Open a bash shell in the GUI container
docker exec -it mohawk-gui bash

# Check Python environment
python --version
pip list | grep PyQt6
```

## Production Considerations

For production deployments:

1. **Use environment variables** for configuration instead of command-line args
2. **Enable SSL/TLS** with `--ssl-enabled` and proper certificate paths
3. **Use volume mounts** for persistent model storage: `docker volume create mohawk-models`
4. **Add resource limits** in docker-compose.yml:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '4'
         memory: 8G
   ```
5. **Use Docker secrets** for sensitive credentials (keys, tokens)
6. **Set up monitoring** with Prometheus + Grafana for metrics
7. **Enable log rotation** to prevent disk space issues

## Next Steps

1. **Customize worker configuration** in `prototype/worker_secure.py`
2. **Add model loading logic** to `mohawk_gui/main_window.py`
3. **Configure SSL certificates** in `./certs/` directory
4. **Set up CI/CD pipelines** to build and push images to a registry
5. **Deploy to cloud** (Docker Swarm, Kubernetes, or cloud container services)

## Quick Reference

```bash
# Start everything
docker compose up -d && python mohawk_gui/main.py

# Stop everything
docker compose down

# View all logs
docker compose logs -f

# Rebuild containers (after code changes)
docker compose up -d --build

# Remove everything including volumes
docker compose down -v
```

## Support & Documentation

- Docker Compose: https://docs.docker.com/compose/
- PyQt6: https://www.riverbankcomputing.com/software/pyqt/
- Mohawk Inference Engine: See README.md in project root
