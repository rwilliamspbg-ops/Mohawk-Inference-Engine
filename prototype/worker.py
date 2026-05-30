from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import uvicorn
import asyncio
import pickle
from typing import Dict
from prototype.model_tools import ToyModel
import base64

app = FastAPI()

slices: Dict[str, ToyModel] = {}

class PreloadRequest(BaseModel):
    slice_id: str
    manifest: dict
    weights_b64: str

class ExecRequest(BaseModel):
    slice_id: str
    input_b64: str

@app.post("/preload")
async def preload(req: PreloadRequest):
    try:
        blob = base64.b64decode(req.weights_b64)
        m = ToyModel.deserialize(blob)
        slices[req.slice_id] = m
        return {"status": "ok", "slice_id": req.slice_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/execute")
async def execute(req: ExecRequest):
    if req.slice_id not in slices:
        raise HTTPException(status_code=404, detail="slice not found")
    blob = base64.b64decode(req.input_b64)
    x = pickle.loads(blob)
    out = slices[req.slice_id].apply(x)
    out_blob = pickle.dumps(out)
    return {"output_b64": base64.b64encode(out_blob).decode('ascii')}

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', type=int, default=8000)
    args = p.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
