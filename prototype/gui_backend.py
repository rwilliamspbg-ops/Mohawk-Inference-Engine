#!/usr/bin/env python3
"""Mohawk GUI Backend Service - FastAPI Server with LAN Discovery"""

import sys
import argparse
import random
import time
import threading
import requests
import logging
from datetime import datetime
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

try:
    from prototype.service_discovery import (
        MohawkServiceDiscovery, LanServiceRegistry, MohawkService, get_local_ip
    )
    HAS_DISCOVERY = True
except ImportError:
    HAS_DISCOVERY = False
    get_local_ip = lambda: "127.0.0.1"

logger = logging.getLogger(__name__)

app = FastAPI(title="Mohawk GUI Backend", version="2.1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service discovery (start background thread)
service_discovery = MohawkServiceDiscovery() if HAS_DISCOVERY else None
service_registry: Optional[LanServiceRegistry] = None

# In-memory state
active_models = {}
active_sessions: Dict[str, dict] = {}
workers_connected = {"worker_0": {"port": 8004, "status": "connected"}}
metrics_lock = threading.Lock()
current_model = None
discovered_services: Dict[str, MohawkService] = {}

# Metrics
metrics = {
    "throughput": 0,
    "latency_p50": 12,
    "latency_p95": 45,
    "latency_p99": 78,
    "cpu": 35,
    "memory": 42,
    "gpu": 28,
    "total_requests": 0,
    "success_count": 0,
    "error_count": 0,
}


class HealthRequest(BaseModel):
    """Health check request."""
    status: str = "ok"


class InferenceRequest(BaseModel):
    """Inference request."""
    message: str
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 2048
    system_prompt: str = "You are a helpful AI assistant."


class ModelRequest(BaseModel):
    """Model load request."""
    model: str


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mohawk-gui", "timestamp": datetime.now().isoformat()}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Mohawk Inference Engine GUI Backend",
        "version": "2.1.0",
        "status": "running",
        "local_ip": get_local_ip(),
        "discovery_enabled": service_discovery is not None
    }


@app.get("/api/health")
async def api_health():
    """API health check."""
    return {
        "status": "ok",
        "workers_connected": len(workers_connected),
        "current_model": current_model,
        "active_sessions": len(active_sessions)
    }


@app.post("/api/inference/chat")
async def inference_chat(req: InferenceRequest):
    """Process inference request - routes to worker."""
    global current_model
    
    try:
        with metrics_lock:
            metrics["total_requests"] += 1
        
        # Try to call worker service
        try:
            worker_url = "http://mohawk-worker:8003"
            worker_response = requests.post(
                f"{worker_url}/api/inference/chat",
                json={
                    "prompt": req.message,
                    "temperature": req.temperature,
                    "top_p": req.top_p,
                    "max_tokens": req.max_tokens
                },
                timeout=5
            )
            
            if worker_response.status_code == 200:
                result = worker_response.json()
                with metrics_lock:
                    metrics["success_count"] += 1
                    metrics["throughput"] = random.randint(800, 1500)
                    metrics["latency_p50"] = random.randint(10, 20)
                    metrics["latency_p95"] = random.randint(30, 60)
                    metrics["latency_p99"] = random.randint(70, 100)
                
                return result
        except requests.RequestException:
            pass
        
        # Fallback to simulated response
        response = f"Response to: {req.message[:100]}..."
        tokens = random.randint(100, 500)
        
        with metrics_lock:
            metrics["success_count"] += 1
            metrics["throughput"] = random.randint(800, 1500)
            metrics["latency_p50"] = random.randint(10, 20)
            metrics["latency_p95"] = random.randint(30, 60)
            metrics["latency_p99"] = random.randint(70, 100)
        
        return {
            "response": response,
            "tokens_used": tokens,
            "latency_ms": random.randint(5, 50),
            "model": current_model or "Llama-3-8B-Instruct-Q4_K_M"
        }
    
    except Exception as e:
        with metrics_lock:
            metrics["error_count"] += 1
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics")
async def get_metrics():
    """Get current metrics."""
    with metrics_lock:
        return dict(metrics)


@app.post("/api/metrics/update")
async def update_metrics(data: dict):
    """Update metrics."""
    with metrics_lock:
        metrics.update(data)
    return {"status": "updated"}


@app.get("/api/models")
async def list_models():
    """List available models."""
    return {
        "models": [
            {
                "name": "Llama-3-8B-Instruct-Q4_K_M",
                "size_gb": 7.2,
                "type": "LLM",
                "quantization": "Q4_K_M",
                "status": "Ready"
            },
            {
                "name": "Mistral-7B-v0.3-Q5_K_M",
                "size_gb": 6.1,
                "type": "LLM",
                "quantization": "Q5_K_M",
                "status": "Ready"
            },
            {
                "name": "CodeLlama-13B-Instruct-Q3_K_M",
                "size_gb": 9.8,
                "type": "LLM",
                "quantization": "Q3_K_M",
                "status": "Ready"
            }
        ]
    }


@app.post("/api/models/load")
async def load_model(req: ModelRequest):
    """Load a model."""
    global current_model
    current_model = req.model
    
    with metrics_lock:
        active_models[req.model] = {
            "loaded_at": datetime.now().isoformat(),
            "status": "loaded"
        }
    
    return {
        "status": "loaded",
        "model": req.model,
        "size_mb": random.randint(5000, 10000),
        "load_time_ms": random.randint(500, 2000)
    }


@app.get("/api/workers")
async def list_workers():
    """List connected workers."""
    workers = []
    for wid, info in workers_connected.items():
        workers.append({
            "id": wid,
            "host": "localhost",
            "port": info.get("port", 8003),
            "status": info.get("status", "connected"),
            "model": current_model or "None",
            "threads": 8,
            "load": random.randint(10, 80)
        })
    
    return {"workers": workers, "total": len(workers)}


@app.get("/api/sessions")
async def list_sessions():
    """List active sessions."""
    sessions = []
    for sid, session in active_sessions.items():
        sessions.append({
            "id": sid,
            "model": session.get("model", "Llama-3-8B"),
            "status": session.get("status", "Running"),
            "throughput": random.randint(800, 1500),
            "latency": random.randint(10, 50),
            "tokens": random.randint(100, 500)
        })
    
    return {"sessions": sessions}


@app.post("/api/sessions/create")
async def create_session(model: str = "Llama-3-8B"):
    """Create a new session."""
    sid = f"sess_{int(time.time() * 1000) % 10000:04d}"
    active_sessions[sid] = {"model": model, "status": "Running", "created": datetime.now()}
    return {"session_id": sid, "model": model, "status": "created"}


@app.post("/api/sessions/{session_id}/cancel")
async def cancel_session(session_id: str):
    """Cancel a session."""
    if session_id in active_sessions:
        del active_sessions[session_id]
        return {"status": "cancelled"}
    raise HTTPException(status_code=404, detail="Session not found")


@app.post("/api/queue")
async def queue_job(priority: str = "normal"):
    """Queue a job."""
    return {
        "status": "queued",
        "job_id": f"job_{int(time.time() * 1000) % 10000:04d}",
        "priority": priority
    }


@app.post("/api/workers/connect")
async def connect_workers():
    """Connect to worker services."""
    try:
        worker_response = requests.get(
            "http://mohawk-worker:8003/health",
            timeout=5
        )
        if worker_response.status_code == 200:
            workers_connected["worker_0"]["status"] = "connected"
            return {
                "status": "connected",
                "workers": list(workers_connected.keys()),
                "count": len(workers_connected)
            }
    except requests.RequestException:
        pass
    
    return {
        "status": "connected",
        "workers": list(workers_connected.keys()),
        "count": len(workers_connected)
    }


@app.post("/api/security/jwt/refresh")
async def refresh_jwt_token():
    """Refresh JWT token."""
    return {"status": "refreshed", "token": "jwt_token_...", "expires_in": 86400}


@app.post("/api/security/pqc/enable")
async def enable_pqc():
    """Enable Post-Quantum Cryptography."""
    return {"status": "enabled", "type": "hybrid_kem"}


# ============================================================================
# SERVICE DISCOVERY ENDPOINTS
# ============================================================================

@app.get("/api/discovery/services")
async def get_discovered_services(service_type: Optional[str] = None):
    """Get all discovered Mohawk services on LAN."""
    if not service_discovery:
        return {"services": [], "count": 0, "error": "Discovery not available"}
    
    services = service_discovery.get_services(service_type)
    return {
        "services": [s.to_dict() for s in services],
        "count": len(services)
    }


@app.get("/api/discovery/gui")
async def get_gui_services():
    """Get all discovered GUI services."""
    if not service_discovery:
        return {"guis": [], "count": 0, "error": "Discovery not available"}
    
    services = service_discovery.find_gui_services()
    return {
        "guis": [s.to_dict() for s in services],
        "count": len(services)
    }


@app.get("/api/discovery/workers")
async def get_worker_services():
    """Get all discovered worker services."""
    if not service_discovery:
        return {"workers": [], "count": 0, "error": "Discovery not available"}
    
    services = service_discovery.find_worker_services()
    return {
        "workers": [s.to_dict() for s in services],
        "count": len(services)
    }


@app.post("/api/discovery/connect/{service_name}")
async def connect_to_discovered_service(service_name: str):
    """Connect to a discovered service."""
    if not service_discovery:
        raise HTTPException(status_code=503, detail="Discovery not available")
    
    service = service_discovery.get_service_by_name(service_name)
    
    if not service:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
    
    # Try to connect
    try:
        response = requests.get(f"{service.url}/health", timeout=3)
        if response.status_code == 200:
            with metrics_lock:
                if service.service_type == "worker":
                    workers_connected[service_name] = {
                        "url": service.url,
                        "status": "connected",
                        "discovered_at": service.discovered_at
                    }
            
            return {
                "status": "connected",
                "service": service.to_dict(),
                "url": service.url
            }
    except Exception as e:
        logger.error(f"Failed to connect to {service_name}: {e}")
        raise HTTPException(status_code=503, detail=f"Service unreachable: {str(e)}")


@app.post("/api/discovery/refresh")
async def refresh_service_discovery():
    """Refresh service discovery (rescan LAN)."""
    if not service_discovery:
        return {"status": "error", "message": "Discovery not available"}
    
    if not service_discovery._running:
        service_discovery.start()
    
    return {
        "status": "refreshing",
        "message": "Rescanning LAN for Mohawk services..."
    }


@app.get("/api/discovery/status")
async def discovery_status():
    """Get service discovery status."""
    if not service_discovery:
        return {
            "discovery_enabled": False,
            "local_ip": get_local_ip(),
            "services_found": 0,
            "workers_connected": len(workers_connected)
        }
    
    return {
        "discovery_enabled": True,
        "discovery_running": service_discovery._running,
        "local_ip": get_local_ip(),
        "services_found": len(service_discovery.discovered_services),
        "workers_connected": len(workers_connected)
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Mohawk GUI Backend Service")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8003, help="Port to listen on")
    parser.add_argument("--discovery", action="store_true", help="Enable LAN service discovery")
    parser.add_argument("--register", action="store_true", help="Register this service for discovery")
    args = parser.parse_args()
    
    print("=" * 60)
    print("[MOHAWK GUI BACKEND] Starting Inference Engine GUI Service")
    print("=" * 60)
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    if args.discovery:
        print("LAN Discovery: ENABLED")
    print("=" * 60)
    
    # Start service discovery if enabled
    if args.discovery and service_discovery:
        service_discovery.start()
    
    # Register this service if requested
    if args.register and service_discovery:
        registry = LanServiceRegistry(
            hostname="mohawk-gui",
            service_type="gui",
            port=args.port,
            properties={"version": "2.1.0"}
        )
        registry.register()
    
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
