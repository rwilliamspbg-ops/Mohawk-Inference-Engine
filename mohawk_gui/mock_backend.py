"""Lightweight backend API used by docker-compose for local GUI verification."""

from datetime import datetime
from fastapi import FastAPI

app = FastAPI(title="Mohawk GUI Mock Backend", version="1.0.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "service": "mohawk-gui-backend"}


@app.get("/api/workers")
async def list_workers() -> dict:
    return {
        "workers": [
            {
                "id": "worker_0",
                "host": "localhost",
                "port": 8003,
                "status": "Connected",
                "model": "Llama-3-8B",
                "threads": 8,
                "load": 25,
            },
            {
                "id": "worker_1",
                "host": "localhost",
                "port": 8004,
                "status": "Connected",
                "model": "Mistral-7B",
                "threads": 8,
                "load": 18,
            },
        ]
    }


@app.post("/api/workers/connect")
async def connect_workers() -> dict:
    return {"status": "ok", "connected": 2}


@app.get("/api/metrics")
async def metrics() -> dict:
    # Keep values in GUI progress bar ranges.
    return {
        "metrics": {
            "throughput": 420,
            "cpu": 31,
            "memory": 44,
            "gpu": 27,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    }


@app.get("/api/sessions")
async def sessions() -> dict:
    return {
        "sessions": [
            {
                "id": "sess_001",
                "model": "Llama-3-8B",
                "status": "Running",
                "throughput": 420,
                "latency": 23,
                "tokens": 1980,
            }
        ]
    }


@app.post("/api/sessions/{session_id}/cancel")
async def cancel_session(session_id: str) -> dict:
    return {"status": "ok", "cancelled": session_id}
