# Quick Start Guide - Mohawk Inference Engine

## TL;DR - Get Running in 3 Steps

### Step 1: Start Docker Containers
```bash
docker compose up -d
```

### Step 2: Verify Containers Are Running
```bash
docker ps
# Both containers should show "healthy" status
```

### Step 3: Launch the GUI Locally
```bash
python mohawk_gui/main.py
```

Done! The PyQt6 GUI is now running on your machine and connected to Docker backend services.

---

## Architecture

- **PyQt6 GUI** (your machine) → connects to backend
- **Docker Containers** (backend services on ports 8003 & 8004)
  - `mohawk-gui`: Health checks & API endpoints
  - `mohawk-worker`: Inference worker service

---

## System Requirements

✅ **Docker Desktop** or Docker Engine + Docker Compose  
✅ **Python 3.12+** installed locally  
✅ **PyQt6** (install via `pip install -r requirements.txt`)

---

## First-Time Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start backend containers
docker compose up -d

# 3. Run the GUI
python mohawk_gui/main.py

# 4. To stop everything
docker compose down
```

---

## Common Commands

| Command | Purpose |
|---------|---------|
| `docker compose up -d` | Start backend services in background |
| `docker ps` | Check if containers are running |
| `docker logs mohawk-gui -f` | View GUI service logs |
| `docker compose down` | Stop all containers |
| `python mohawk_gui/main.py` | Launch GUI on your machine |
| `docker compose down -v` | Stop containers and delete volumes |

---

## Need Help?

- **Containers won't start?** → Check `docker ps -a` for errors, then see DOCKER_SETUP.md
- **GUI won't connect?** → Verify containers are healthy: `docker ps` should show "Up X seconds (healthy)"
- **PyQt6 import errors?** → Install system packages (see DOCKER_SETUP.md "Troubleshooting")
- **Full setup guide** → See `DOCKER_SETUP.md` for detailed instructions

---

## Project Structure

```
.
├── Dockerfile              # GUI container image
├── Dockerfile.worker       # Worker container image
├── docker-compose.yml      # Container orchestration
├── DOCKER_SETUP.md        # Detailed Docker guide (THIS FILE)
├── QUICKSTART.md          # Quick reference (THIS FILE)
├── mohawk_gui/
│   ├── main.py            # Entry point - run this locally
│   ├── main_window.py     # PyQt6 GUI implementation
│   ├── auth_manager.py    # Security/authentication
│   └── ...
├── prototype/
│   ├── worker_secure.py   # Inference worker backend
│   └── ...
└── requirements.txt       # Python dependencies
```

---

## Next Steps

1. Explore the dashboard features (Model Library, Chat, Metrics, etc.)
2. Add your own models to `./models/` directory
3. Configure workers in the Worker Config tab
4. Check security settings in Security Center tab
5. Monitor performance on the Metrics dashboard

Enjoy! 🦅
