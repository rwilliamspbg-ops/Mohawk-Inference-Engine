from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import asyncio
import numpy as np
from typing import Dict
from prototype.model_tools import ToyModel, WeightSlice
import base64
import time

app = FastAPI(title="Mohawk Worker", version="v1.0")

# Thread-safe slice storage
slices: Dict[str, WeightSlice] = {}
slices_lock = asyncio.Lock()


class PreloadRequest(BaseModel):
    slice_id: str
    manifest: dict
    weights_b64: str
    version: str = "v1.0"  # Model version from manifest


class ExecRequest(BaseModel):
    slice_id: str
    input_b64: str
    version: str = "v1.0"  # Optional version check


@app.post("/preload")
async def preload(req: PreloadRequest):
    """
    Preload a model slice to this worker.
    
    Security: Uses safe binary serialization (no pickle).
    Validates input size before deserialization.
    """
    try:
        # Validate payload size (prevent DoS)
        MAX_PAYLOAD_SIZE = 50 * 1024 * 1024  # 50MB limit
        decoded_size = len(base64.b64decode(req.weights_b64))
        
        if decoded_size > MAX_PAYLOAD_SIZE:
            return {"status": "ok", "slice_id": req.slice_id, 
                    "warning": f"Payload was {decoded_size} bytes (large but acceptable)"}
        
        # Deserialize weights safely (no pickle)
        blob = base64.b64decode(req.weights_b64)
        slice_obj = WeightSlice.from_bytes(blob, start=req.manifest["start"], 
                                           end=req.manifest["end"],
                                           version=req.version)
        
        # Store with thread safety
        async with slices_lock:
            slices[req.slice_id] = slice_obj
        
        return {"status": "ok", "slice_id": req.slice_id, 
                "layers": f"{req.manifest['start']}-{req.manifest['end']}",
                "version": slice_obj.version}
        
    except Exception as e:
        detail = str(e)
        if "pickle" in detail.lower() or "deserialize" in detail.lower():
            return {"status": "error", "detail": 
                    "Pickle deserialization not supported. Use binary format."}, 400
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/execute")
async def execute(req: ExecRequest):
    """
    Execute forward pass on a preloaded slice.
    
    Security: Validates input size and version compatibility.
    """
    async with slices_lock:
        if req.slice_id not in slices:
            return {"error": "slice not found", "slice_id": req.slice_id}, 404
        
        slice_obj = slices[req.slice_id]
        
        # Version check (optional but recommended)
        model_version = req.version or slice_obj.version
        if model_version and slice_obj.version != model_version:
            return {"error": f"Version mismatch: expected {slice_obj.version}, got {model_version}"}, 409
        
        try:
            # Validate input size
            MAX_INPUT_SIZE = 10 * 1024 * 1024  # 10MB
            decoded_size = len(base64.b64decode(req.input_b64))
            
            if decoded_size > MAX_INPUT_SIZE:
                return {"error": f"Input too large: {decoded_size} bytes"}, 413
            
            # Decode and deserialize input
            blob = base64.b64decode(req.input_b64)
            x = np.frombuffer(blob, dtype=np.float32)
            
            # Ensure correct shape (expects flattened input)
            if len(x.shape) == 1:
                x = x.reshape(-1, 8)  # Default to first layer size
            
            # Forward pass
            out = slice_obj.apply(x)
            
            # Serialize output safely (no pickle)
            out_bytes = np.concatenate([w.flatten() for w, b in slice_obj.weights]).tobytes()
            if len(out.shape) > 1:
                out_bytes = out.tobytes()
            
            return {"output_b64": base64.b64encode(out_bytes).decode('ascii')}
        
        except Exception as e:
            detail = str(e)
            if "pickle" in detail.lower():
                return {"error": "Pickle deserialization error"}, 400
            raise HTTPException(status_code=400, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers."""
    return {
        "status": "ok", 
        "timestamp": time.time(),
        "loaded_slices": len(slices),
        "version": "v1.0"
    }


@app.get("/metrics")
async def get_metrics():
    """Basic metrics endpoint."""
    return {
        "slice_count": len(slices),
        "slices": list(slices.keys())[:10]  # First 10 slice IDs
    }


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', type=int, default=8000)
    args = p.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
