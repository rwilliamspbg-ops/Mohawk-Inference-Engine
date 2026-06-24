# Mohawk Inference Engine - Linux Build Guide

## Prerequisites

### Ubuntu/Debian (ARMv7/ARM64/x86_64)

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install build tools (required for pip compilation on ARM64)
sudo apt-get install -y \
    build-essential \
    python3-dev \
    python3-venv \
    python3-pip \
    git \
    curl \
    libffi-dev \
    libssl-dev \
    pkg-config \
    avahi-daemon

# Start avahi for mDNS service discovery
sudo systemctl start avahi-daemon
sudo systemctl enable avahi-daemon
```

### Alpine Linux (Lightweight - Use Only if Required)

Note: Alpine is not recommended for Mohawk due to PyQt6 build complexity.

```bash
apk add --no-cache \
    build-base \
    python3-dev \
    py3-pip \
    git \
    curl \
    libffi-dev \
    openssl-dev \
    pkgconfig \
    avahi
```

## Docker Build (Recommended)

### Build Locally (Optimized for Your Architecture)

```bash
cd ~/mohawk-inference-engine

# Build for current architecture (auto-detects ARM64, x86_64, etc.)
docker build -f Dockerfile -t mohawk-gui:latest .
docker build -f Dockerfile.worker -t mohawk-worker:latest .

# Or build with buildx for cross-platform (requires Docker Buildx)
docker buildx build --load -f Dockerfile -t mohawk-gui:latest .
docker buildx build --load -f Dockerfile.worker -t mohawk-worker:latest .
```

### Start Containers

```bash
# Create Docker network
docker network create mohawk-network

# Run worker
docker run -d --name mohawk-worker \
  -p 8004:8003 \
  --network mohawk-network \
  -v $(pwd)/models:/app/models \
  -e PYTHONUNBUFFERED=1 \
  mohawk-worker:latest

# Run GUI backend
docker run -d --name mohawk-gui \
  -p 8003:8003 \
  --network mohawk-network \
  -e PYTHONUNBUFFERED=1 \
  -e DISCOVERY=true \
  mohawk-gui:latest

# Check logs
docker logs -f mohawk-gui
docker logs -f mohawk-worker
```

## Native Python Setup (Non-Docker)

### Create Virtual Environment

```bash
# Create venv
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# OR
# venv\Scripts\activate  # Windows

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install requirements
pip install -r requirements.txt

# Install extra FastAPI dependencies
pip install fastapi uvicorn requests
```

### Run Services

```bash
# Terminal 1: Worker
python -m uvicorn prototype.worker_secure:app --host 0.0.0.0 --port 8004

# Terminal 2: GUI Backend
python -m uvicorn prototype.gui_backend:app --host 0.0.0.0 --port 8003 --discovery --register
```

## LAN Service Discovery

### Enable Discovery

The system now supports automatic LAN discovery using mDNS/Zeroconf.

**In Docker:**
```bash
docker run -d --name mohawk-gui \
  -p 8003:8003 \
  --network mohawk-network \
  -e DISCOVERY=true \
  mohawk-gui:latest
```

**Native:**
```bash
python -m uvicorn prototype.gui_backend:app \
  --host 0.0.0.0 \
  --port 8003 \
  --discovery \
  --register
```

### Query Services from Client

```bash
# Get all discovered services
curl http://localhost:8003/api/discovery/services

# Get discovered workers
curl http://localhost:8003/api/discovery/workers

# Get discovery status
curl http://localhost:8003/api/discovery/status

# Connect to a discovered service
curl -X POST http://localhost:8003/api/discovery/connect/mohawk-worker
```

## Troubleshooting

### Python 3.12 Not Available

Use alternative versions:
```bash
# Ubuntu 22.04 LTS (has Python 3.10 by default)
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv python3.12-dev

# Then create venv with explicit version
python3.12 -m venv venv
```

### ARM64 Build Issues

If pip compilation fails on ARM64:

```bash
# Install LLVM for Rust dependencies
sudo apt-get install -y llvm-14 llvm-14-dev

# Install additional build tools
sudo apt-get install -y cargo rustc

# Set compiler flags
export LDFLAGS="-L/usr/lib/$(dpkg-architecture -q DEB_HOST_MULTIARCH)"
```

### PyQt6 Build Fails

PyQt6 requires Qt development libraries on Linux:

```bash
# Debian/Ubuntu
sudo apt-get install -y \
    qtbase5-dev \
    qtdeclarative5-dev \
    libqt5gui5 \
    libqt5core5a \
    libqt5dbus5

# If still failing, use pre-built wheels
pip install --only-binary :all: PyQt6
```

### mDNS Not Resolving

Ensure avahi-daemon is running:

```bash
sudo systemctl start avahi-daemon
sudo systemctl status avahi-daemon

# Test mDNS resolution
avahi-browse -a  # List all services
avahi-resolve-host-name mohawk-gui.local
```

### Docker Image Size

To reduce image size on ARM64:

```bash
# Use multi-stage build
docker build \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  -f Dockerfile.slim \
  -t mohawk-gui:slim .
```

## Docker Compose (Recommended for Full Stack)

```bash
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f

# Stop all
docker compose down
```

See `docker-compose.yml` for configuration.

## Performance Tuning for iProda

### ARM64 Specific Optimizations

```bash
# In docker-compose.yml or docker run:
docker run -d \
  --cpus="2" \
  --memory="2g" \
  --memory-swap="2g" \
  --cpuset-cpus="0-3" \
  mohawk-worker:latest
```

### GPU Support (If Available)

```bash
docker run -d \
  --runtime=nvidia \
  --gpus all \
  mohawk-worker:latest
```

## Verification

```bash
# Check GUI backend
curl http://localhost:8003/health

# Check worker
curl http://localhost:8004/health

# List models
curl http://localhost:8003/api/models

# Test chat
curl -X POST http://localhost:8003/api/inference/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","temperature":0.7}'

# Check discovery
curl http://localhost:8003/api/discovery/status
```

## Next Steps

1. Start containers with `docker compose up -d`
2. Launch GUI client: `python mohawk_gui/main.py`
3. Services will auto-discover each other on LAN
4. Configure models and start inferencing

For production deployment on iProda, see DEPLOYMENT.md
