from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import uvicorn
import asyncio
import pickle
from typing import Dict
from prototype.model_tools import ToyModel
import base64
from prototype.crypto import PQCAdapter, AEAD, b64, ub64
from prototype.telemetry import Telemetry
import traceback
import threading
from fastapi.responses import JSONResponse

app = FastAPI()

slices: Dict[str, ToyModel] = {}
keys: Dict[str, AEAD] = {}  # peer_pub_b64 -> AEAD

# simple in-memory metrics
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
    client_pub = ub64(req.client_pub_b64)
    client_id = req.client_id or 'controller'
    kem = PQCAdapter()
    worker_pub = kem.public_bytes()
    # if the controller provided an OQS pub, attempt hybrid KEM
    controller_oqs_pub = None
    shared_oqs = None
    if getattr(req, 'oqs_pub_b64', None):
        try:
            controller_oqs_pub = ub64(req.oqs_pub_b64)
        except Exception:
            controller_oqs_pub = None
    # always derive X25519 shared
    x25519_key = kem.derive_shared(client_pub)
    # if both sides support OQS, encapsulate to controller's OQS pub and
    # derive a hybrid AEAD key
    if controller_oqs_pub and kem.oqs_supported:
        try:
            ct, shared_oqs = kem.encap(controller_oqs_pub)
        except Exception:
            ct = None
            shared_oqs = None
    else:
        ct = None
        shared_oqs = None
    # final AEAD key: hybrid if we have an OQS shared secret, else X25519-only
    try:
        from prototype.crypto import derive_hybrid_key
        if shared_oqs:
            final_key = derive_hybrid_key(x25519_key, shared_oqs)
        else:
            final_key = x25519_key
    except Exception:
        final_key = x25519_key
    # store AEAD keyed by client id for stable lookup
    keys[client_id] = AEAD(final_key)
    with metrics_lock:
        metrics['handshakes'] += 1
    # include worker-side OQS public bytes and encapsulation ct if available
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
    try:
        if req.encrypted:
            # find AEAD by matching any key (simple demo: single client)
            # use controller client id mapping
            if 'controller' not in keys:
                raise HTTPException(status_code=400, detail='no handshake for controller')
            aead = keys['controller']
            nonce = ub64(req.nonce_b64)
            ct = ub64(req.weights_b64)
            blob = aead.decrypt(nonce, ct)
        else:
            blob = base64.b64decode(req.weights_b64)
        m = ToyModel.deserialize(blob)
        slices[req.slice_id] = m
        with metrics_lock:
            metrics['preload_success'] += 1
        return {"status": "ok", "slice_id": req.slice_id}
    except Exception as e:
        tb = traceback.format_exc()
        print("preload error:\n", tb)
        with metrics_lock:
            metrics['preload_fail'] += 1
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/execute")
@telemetry.timed('execute_time_sum', 'execute_time_count')
async def execute(req: ExecRequest):
    if req.slice_id not in slices:
        raise HTTPException(status_code=404, detail="slice not found")
    try:
        if req.encrypted:
            if 'controller' not in keys:
                raise HTTPException(status_code=400, detail='no handshake for controller')
            aead = keys['controller']
            nonce = ub64(req.nonce_b64)
            ct = ub64(req.input_b64)
            blob = aead.decrypt(nonce, ct)
        else:
            blob = base64.b64decode(req.input_b64)
        x = pickle.loads(blob)
        out = slices[req.slice_id].apply(x)
        out_blob = pickle.dumps(out)
        # maybe encrypt response if request was encrypted
        if req.encrypted:
            nonce, ct = aead.encrypt(out_blob)
            with metrics_lock:
                metrics['execute_success'] += 1
            return {"encrypted": True, "nonce_b64": b64(nonce), "output_b64": b64(ct)}
        else:
            with metrics_lock:
                metrics['execute_success'] += 1
            return {"output_b64": base64.b64encode(out_blob).decode('ascii')}
    except Exception as e:
        tb = traceback.format_exc()
        print("execute error:\n", tb)
        with metrics_lock:
            metrics['execute_fail'] += 1
        raise HTTPException(status_code=400, detail=str(e))


@app.get('/metrics')
async def get_metrics():
    with metrics_lock:
        return JSONResponse(content=dict(metrics))

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', type=int, default=8000)
    args = p.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
