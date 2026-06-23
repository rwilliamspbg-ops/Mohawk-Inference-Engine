"""Controller API used by the desktop GUI for end-to-end wiring verification."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Mohawk Controller Service", version="1.0.0")


class LoadModelRequest(BaseModel):
    model: str


class ChatRequest(BaseModel):
    message: str
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 2048
    system_prompt: str = "You are a helpful AI assistant."


class QueueRequest(BaseModel):
    priority: str = "normal"


class AddWorkerRequest(BaseModel):
    host: str
    port: int


class DownloadModelRequest(BaseModel):
    model_id: str


STATE = {
    "workers": [],
    "models": [
        {
            "name": "Llama-3-8B-Instruct-Q4_K_M",
            "size_gb": 7.2,
            "type": "LLM",
            "quantization": "Q4_K_M",
            "status": "Ready",
        },
        {
            "name": "Mistral-7B-v0.3-Q5_K_M",
            "size_gb": 6.1,
            "type": "LLM",
            "quantization": "Q5_K_M",
            "status": "Ready",
        },
    ],
    "current_model": None,
    "sessions": [],
    "queue": [],
    "security": {
        "jwt_refresh_count": 0,
        "pqc_enabled": False,
    },
}


def _worker_urls() -> list[str]:
    raw = os.getenv("WORKER_URLS", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _worker_host_port(worker_url: str) -> tuple[str, int]:
    parsed = urlparse(worker_url)
    host = parsed.hostname or worker_url.split("://", 1)[-1].split(":", 1)[0]
    port = parsed.port or 8000
    return host, port


def _worker_entries_from_env() -> list[dict]:
    workers = []
    for index, worker_url in enumerate(_worker_urls()):
        host, port = _worker_host_port(worker_url)
        workers.append(
            {
                "id": f"worker_{index}",
                "host": host,
                "port": port,
                "status": "Connected",
                "model": STATE["current_model"] or "Distributed",
                "threads": 8,
                "load": 20 + index * 5,
            }
        )
    return workers


def _merged_workers() -> list[dict]:
    env_workers = _worker_entries_from_env()
    extra = STATE["workers"]
    merged = list(env_workers)
    seen = {(w["host"], w["port"]) for w in merged}
    for worker in extra:
        key = (worker["host"], worker["port"])
        if key not in seen:
            merged.append(worker)
    return merged


def _session_status() -> str:
    return "Running" if STATE["current_model"] else "Idle"


def _synthesize_sessions() -> list[dict]:
    if STATE["sessions"]:
        return STATE["sessions"]

    return [
        {
            "id": "sess_001",
            "model": STATE["current_model"] or "No model loaded",
            "status": _session_status(),
            "throughput": 350 if STATE["current_model"] else 0,
            "latency": 24 if STATE["current_model"] else 0,
            "tokens": 2100 if STATE["current_model"] else 0,
        }
    ]


def _check_worker_health(host: str, port: int) -> str:
    try:
        r = requests.get(f"http://{host}:{port}/health", timeout=1)
        return "Connected" if r.status_code == 200 else "Degraded"
    except Exception:
        return "Disconnected"


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "service": "controller"}


@app.get("/api/models")
async def list_models() -> dict:
    return {
        "models": STATE["models"],
        "current_model": STATE["current_model"],
    }


@app.post("/api/models/load")
async def load_model(request: LoadModelRequest) -> dict:
    STATE["current_model"] = request.model
    for model in STATE["models"]:
        model["status"] = "Loaded" if model["name"] == request.model else "Ready"
    return {"status": "ok", "model": request.model}


@app.post("/api/models/download")
async def download_model(request: DownloadModelRequest) -> dict:
    model_name = request.model_id.strip()
    if not model_name:
        return {"error": "model_id is required"}

    for model in STATE["models"]:
        if model["name"] == model_name:
            return {"status": "ok", "model": model_name, "message": "Model already exists"}

    STATE["models"].append(
        {
            "name": model_name,
            "size_gb": 0.0,
            "type": "LLM",
            "quantization": "Unknown",
            "status": "Ready",
        }
    )
    return {"status": "ok", "model": model_name}


@app.get("/api/workers")
async def list_workers() -> dict:
    workers = _merged_workers()
    for worker in workers:
        worker["status"] = _check_worker_health(worker["host"], worker["port"])
        worker["model"] = STATE["current_model"] or worker.get("model", "Distributed")

    return {"workers": workers}


@app.post("/api/workers/connect")
async def connect_workers() -> dict:
    workers = _merged_workers()
    connected = sum(
        1 for worker in workers if _check_worker_health(worker["host"], worker["port"]) == "Connected"
    )
    return {"status": "ok", "connected": connected, "total": len(workers)}


@app.post("/api/workers/add")
async def add_worker(request: AddWorkerRequest) -> dict:
    worker = {
        "id": f"worker_custom_{len(STATE['workers']) + 1}",
        "host": request.host.strip(),
        "port": request.port,
        "status": "Unknown",
        "model": STATE["current_model"] or "Distributed",
        "threads": 8,
        "load": 0,
    }
    STATE["workers"].append(worker)
    return {"status": "ok", "worker": worker}


@app.post("/api/queue")
async def queue_job(request: QueueRequest) -> dict:
    job = {
        "id": f"job_{uuid.uuid4().hex[:8]}",
        "priority": request.priority,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    STATE["queue"].append(job)
    return {"status": "ok", "job": job}


@app.post("/api/inference/chat")
async def chat_inference(request: ChatRequest) -> dict:
    model = STATE["current_model"] or "No model loaded"
    truncated = request.message.strip()[:240]
    response = (
        f"[{model}] {truncated}"
        if truncated
        else f"[{model}] Please send a non-empty message."
    )
    return {"status": "ok", "response": response}


@app.get("/api/metrics")
async def metrics() -> dict:
    workers = _merged_workers()
    connected = sum(
        1 for worker in workers if _check_worker_health(worker["host"], worker["port"]) == "Connected"
    )
    worker_count = max(len(workers), 1)
    return {
        "metrics": {
            "throughput": 300 + connected * 35,
            "cpu": min(95, 28 + worker_count),
            "memory": min(95, 40 + worker_count),
            "gpu": min(95, 22 + connected),
            "latency_p50": 20 + worker_count,
            "latency_p95": 35 + worker_count * 2,
            "latency_p99": 60 + worker_count * 2,
            "active_sessions": len(_synthesize_sessions()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }


@app.get("/api/sessions")
async def sessions() -> dict:
    return {"sessions": _synthesize_sessions()}


@app.post("/api/sessions/{session_id}/cancel")
async def cancel_session(session_id: str) -> dict:
    STATE["sessions"] = [s for s in STATE["sessions"] if s.get("id") != session_id]
    return {"status": "ok", "cancelled": session_id}


@app.post("/api/security/jwt/refresh")
async def refresh_jwt() -> dict:
    STATE["security"]["jwt_refresh_count"] += 1
    return {
        "status": "ok",
        "refresh_count": STATE["security"]["jwt_refresh_count"],
    }


@app.post("/api/security/pqc/enable")
async def enable_pqc() -> dict:
    STATE["security"]["pqc_enabled"] = True
    return {"status": "ok", "pqc_enabled": True}
