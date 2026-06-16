from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import asyncio
import pickle
from typing import Dict
from prototype.model_tools_v2 import ToyModel
import base64
from prototype.crypto_improved import PQCAdapter, ReplayProtectedAEAD, AEAD, b64, ub64
from prototype.telemetry import Telemetry
import traceback
import threading
from fastapi.responses import JSONResponse

app = FastAPI()

slices: Dict[str, ToyModel] = {}
keys: Dict[str, ReplayProtectedAEAD] = {}  # peer_id -> AEAD with replay protection

# Simple in-memory metrics
metrics = {
    'handshakes': 0,
    'preload_success': 0,
    'preload_fail': 0,
    'execute_success': 0,
    'execute_fail': 0,
}
metrics_lock = threading.Lock()
telemetry = Telemetry(metrics, metrics_lock)


class HandshakeRequest(BaseModel):
    client_pub_b64: str
    client_id: str | None = None
    oqs_pub_b64: str | None = None


class PreloadRequest(BaseModel):
    slice_id: str
    manifest: dict
    weights_b64: str
    encrypted: bool = False
    nonce_b64: str = None


class ExecRequest(BaseModel):
    slice_id: str
    input_b64: str
    encrypted: bool = False
    nonce_b64: str = None


@app.post("/handshake")
async def handshake(req: HandshakeRequest):
    """
    Perform secure handshake with client.
    
    Supports hybrid X25519 + OQS key exchange when liboqs is available.
    Uses ReplayProtectedAEAD for all subsequent encrypted communications.
    """
    client_pub = ub64(req.client_pub_b64)
    client_id = req.client_id or 'controller'
    
    # Initialize KEM for this handshake
    kem = PQCAdapter()
    worker_pub = kem.public_bytes()
    
    # Optional OQS public bytes
    controller_oqs_pub = None
    shared_oqs = None
    
    if getattr(req, 'oqs_pub_b64', None):
        try:
            controller_oqs_pub = ub64(req.oqs_pub_b64)
        except Exception:
            controller_oqs_pub = None
    
    # Always derive X25519 shared secret
    x25519_key = kem.derive_shared(client_pub)
    
    # If both sides support OQS, perform hybrid KEM exchange
    if controller_oqs_pub and kem.oqs_supported:
        try:
            ct, shared_oqs = kem.encap(controller_oqs_pub)
        except Exception:
            ct = None
            shared_oqs = None
    else:
        ct = None
        shared_oqs = None
    
    # Final AEAD key: hybrid if we have OQS shared secret, else X25519-only
    try:
        from prototype.crypto_improved import derive_hybrid_key
        if shared_oqs:
            final_key = derive_hybrid_key(x25519_key, shared_oqs)
        else:
            final_key = x25519_key
    except Exception:
        final_key = x25519_key
    
    # Use ReplayProtectedAEAD for all encrypted communications
    keys[client_id] = ReplayProtectedAEAD(final_key, nonce_expiry_seconds=3600)
    
    with metrics_lock:
        metrics['handshakes'] += 1
    
    # Include worker-side OQS public bytes and encapsulation ct if available
    resp = {"worker_pub_b64": b64(worker_pub)}
    
    try:
        oqs_pub = kem.get_oqs_public()
        if oqs_pub:
            resp['worker_oqs_pub_b64'] = b64(oqs_pub)
    except Exception:
        pass
    
    if ct:
        try:
            resp['worker_oqs_ct_b64'] = b64(ct)
        except Exception:
            pass
    
    return resp


@app.post("/preload")
@telemetry.timed('preload_time_sum', 'preload_time_count')
async def preload(req: PreloadRequest):
    """
    Preload a model slice to this worker.
    
    Supports encrypted transport with replay protection.
    """
    try:
        if req.encrypted:
            # Find AEAD by client ID (supports multiple clients)
            if client_id := req.manifest.get('client_id') or 'controller':
                aead = keys.get(client_id)
                if not aead:
                    raise HTTPException(status_code=400, detail='no handshake for this client')
                
                nonce = ub64(req.nonce_b64)
                ct = ub64(req.weights_b64)
                blob = aead.decrypt(nonce, ct)
            else:
                # Fallback to 'controller' if no client_id in manifest
                aead = keys.get('controller')
                if not aead:
                    raise HTTPException(status_code=400, detail='no handshake for controller')
                
                nonce = ub64(req.nonce_b64)
                ct = ub64(req.weights_b64)
                blob = aead.decrypt(nonce, ct)
        else:
            blob = base64.b64decode(req.weights_b64)
        
        # Deserialize weights safely (no pickle)
        from prototype.model_tools_v2 import WeightSlice
        slice_obj = WeightSlice.from_bytes(blob, start=req.manifest["start"], 
                                           end=req.manifest["end"])
        
        slices[req.slice_id] = slice_obj
        
        with metrics_lock:
            metrics['preload_success'] += 1
        
        return {"status": "ok", "slice_id": req.slice_id}
    
    except Exception as e:
        tb = traceback.format_exc()
        print("preload error:\n", tb)
        
        with metrics_lock:
            metrics['preload_fail'] += 1
        
        # Check for pickle-related errors
        if "pickle" in str(e).lower():
            raise HTTPException(status_code=400, detail="Pickle deserialization not supported")
        
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/execute")
@telemetry.timed('execute_time_sum', 'execute_time_count')
async def execute(req: ExecRequest):
    """
    Execute forward pass on a preloaded slice.
    
    Supports encrypted transport with replay protection.
    """
    if req.slice_id not in slices:
        raise HTTPException(status_code=404, detail="slice not found")
    
    try:
        if req.encrypted:
            client_id = req.manifest.get('client_id') or 'controller'
            aead = keys.get(client_id) if client_id else keys.get('controller')
            
            if not aead:
                raise HTTPException(status_code=400, detail='no handshake for this client')
            
            nonce = ub64(req.nonce_b64)
            ct = ub64(req.input_b64)
            blob = aead.decrypt(nonce, ct)
        else:
            blob = base64.b64decode(req.input_b64)
        
        # Deserialize input
        x = np.frombuffer(blob, dtype=np.float32) if 'np' in dir() else blob
        
        # Forward pass
        out = slices[req.slice_id].apply(x)
        
        # Serialize output safely (no pickle)
        out_bytes = out.tobytes() if hasattr(out, 'tobytes') else str(out).encode()
        
        # Encrypt response if request was encrypted
        if req.encrypted:
            client_id = req.manifest.get('client_id') or 'controller'
            aead = keys.get(client_id) if client_id else keys.get('controller')
            
            nonce, ct = aead.encrypt(out_bytes)
            with metrics_lock:
                metrics['execute_success'] += 1
            
            return {"encrypted": True, "nonce_b64": b64(nonce), "output_b64": b64(ct)}
        else:
            with metrics_lock:
                metrics['execute_success'] += 1
            
            return {"output_b64": base64.b64encode(out_bytes).decode('ascii')}
    
    except Exception as e:
        tb = traceback.format_exc()
        print("execute error:\n", tb)
        
        with metrics_lock:
            metrics['execute_fail'] += 1
        
        if "pickle" in str(e).lower():
            raise HTTPException(status_code=400, detail="Pickle deserialization error")
        
        raise HTTPException(status_code=400, detail=str(e))


@app.get('/metrics')
async def get_metrics():
    """Expose computed percentiles based on histogram buckets."""
    with metrics_lock:
        out = dict(metrics)
    
    def compute_percentiles(prefix):
        hist_keys = [k for k in out.keys() if k.startswith(f"{prefix}_hist_")]
        if not hist_keys:
            return None
        
        buckets = []
        for k in hist_keys:
            b = k.split('_')[-1]
            cnt = out.get(k, 0)
            try:
                if b == '+Inf':
                    val = float('inf')
                else:
                    val = float(b)
                buckets.append((val, cnt))
            except Exception:
                continue
        
        buckets.sort(key=lambda x: x[0])
        total = sum(c for _, c in buckets)
        
        if total == 0:
            return None
        
        def percentile(p):
            target = total * p
            c = 0
            for val, cnt in buckets:
                c += cnt
                if c >= target:
                    return val
            return buckets[-1][0]
        
        return {'p50': percentile(0.5), 'p95': percentile(0.95), 'p99': percentile(0.99)}
    
    for metric_prefix in ['preload_time', 'execute_time']:
        ps = compute_percentiles(metric_prefix)
        if ps:
            out[f"{metric_prefix}_p50"] = ps['p50']
            out[f"{metric_prefix}_p95"] = ps['p95']
            out[f"{metric_prefix}_p99"] = ps['p99']
    
    return JSONResponse(content=out)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', type=int, default=8000)
    args = p.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
