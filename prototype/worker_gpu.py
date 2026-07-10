# prototype/worker_gpu.py (NEW) - Enhanced worker with GPU support
import base64
from typing import Dict, Optional

import numpy as np
import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from vllm import LLM

app = FastAPI()

class GPUSlice:
    """GPU-accelerated slice for distributed inference."""

    def __init__(self, model_slice: torch.nn.Module):
        self.model = model_slice
        self.device = torch.cuda.current_device()

    def forward(self, x: np.ndarray) -> np.ndarray:
        """GPU-accelerated forward pass with CUDA kernel fusion."""
        x_tensor = torch.from_numpy(x).float().to(self.device)

        # Forward pass on GPU
        with torch.no_grad():
            out_tensor = self.model(x_tensor)

        return out_tensor.cpu().numpy()

# Global model registry
model_slices: Dict[str, GPUSlice] = {}

@app.post("/execute-gpu")
async def execute_gpu(req: ExecRequest):
    """GPU-accelerated inference with batch support."""

    if req.slice_id not in model_slices:
        raise HTTPException(status_code=404, detail="slice not found")

    slice_model = model_slices[req.slice_id]
    x = np.ascontiguousarray(req.input_blob)  # Ensure contiguous

    with torch.cuda.amp.autocast():  # Mixed precision
        out = slice_model.forward(x)

    return {"output_b64": base64.b64encode(out).decode("ascii")}
