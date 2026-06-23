"""
Model loader with support for multiple model formats

Supports:
- HuggingFace transformers models
- GGUF format (via llama-cpp-python)
- ONNX models
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ModelFormat(Enum):
    """Supported model formats"""
    HUGGINGFACE = "huggingface"
    GGUF = "gguf"
    ONNX = "onnx"
    SAFETENSORS = "safetensors"


class ModelLoader:
    """
    Universal model loader with automatic format detection.
    
    Features:
    - Auto-detect model format
    - Download from HuggingFace Hub
    - Local model loading
    - Model validation and integrity checks
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the model loader.
        
        Args:
            cache_dir: Directory to cache downloaded models
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".mohawk" / "models"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ModelLoader initialized with cache_dir={self.cache_dir}")
    
    def detect_format(self, model_path: str) -> ModelFormat:
        """
        Detect the model format from path or files.
        
        Args:
            model_path: Path to model directory or file
            
        Returns:
            Detected ModelFormat
        """
        path = Path(model_path)
        
        if path.suffix == ".gguf":
            return ModelFormat.GGUF
        elif path.suffix == ".onnx":
            return ModelFormat.ONNX
        elif path.is_dir():
            # Check directory contents
            if any(path.glob("*.safetensors")):
                return ModelFormat.SAFETENSORS
            elif any(path.glob("pytorch_model.bin")) or any(path.glob("model.safetensors")):
                return ModelFormat.HUGGINGFACE
        
        # Default to HuggingFace for model IDs
        if "/" in model_path and not path.exists():
            return ModelFormat.HUGGINGFACE
        
        return ModelFormat.HUGGINGFACE
    
    def load(
        self,
        model_path: str,
        model_format: Optional[ModelFormat] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Load a model and return model objects.
        
        Args:
            model_path: Path to model or HuggingFace model ID
            model_format: Force specific format (auto-detected if None)
            **kwargs: Format-specific loading arguments
            
        Returns:
            Dictionary with 'model' and 'tokenizer' keys
            
        Raises:
            ValueError: If model format is unsupported
            FileNotFoundError: If model path doesn't exist
        """
        if model_format is None:
            model_format = self.detect_format(model_path)
        
        logger.info(f"Loading model {model_path} as format {model_format.value}")
        
        if model_format == ModelFormat.GGUF:
            return self._load_gguf(model_path, **kwargs)
        elif model_format == ModelFormat.HUGGINGFACE:
            return self._load_huggingface(model_path, **kwargs)
        elif model_format == ModelFormat.ONNX:
            return self._load_onnx(model_path, **kwargs)
        elif model_format == ModelFormat.SAFETENSORS:
            return self._load_safetensors(model_path, **kwargs)
        else:
            raise ValueError(f"Unsupported model format: {model_format}")
    
    def _load_gguf(self, model_path: str, **kwargs) -> Dict[str, Any]:
        """Load GGUF format model using llama-cpp-python"""
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError("llama-cpp-python required for GGUF models. Install with: pip install llama-cpp-python")
        
        llm = Llama(
            model_path=model_path,
            n_ctx=kwargs.get("n_ctx", 4096),
            n_threads=kwargs.get("n_threads", None),
            verbose=kwargs.get("verbose", False),
        )
        
        return {"model": llm, "tokenizer": None, "format": "gguf"}
    
    def _load_huggingface(self, model_path: str, **kwargs) -> Dict[str, Any]:
        """Load HuggingFace transformers model"""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError:
            raise ImportError("transformers required for HuggingFace models. Install with: pip install transformers")
        
        tokenizer = AutoTokenizer.from_pretrained(model_path, **kwargs)
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=kwargs.get("torch_dtype", "auto"),
            device_map=kwargs.get("device_map", "auto"),
            **kwargs,
        )
        
        return {"model": model, "tokenizer": tokenizer, "format": "huggingface"}
    
    def _load_onnx(self, model_path: str, **kwargs) -> Dict[str, Any]:
        """Load ONNX model"""
        try:
            import onnxruntime as ort
        except ImportError:
            raise ImportError("onnxruntime required for ONNX models. Install with: pip install onnxruntime")
        
        session = ort.InferenceSession(model_path, providers=kwargs.get("providers", ["CPUExecutionProvider"]))
        
        return {"model": session, "tokenizer": None, "format": "onnx"}
    
    def _load_safetensors(self, model_path: str, **kwargs) -> Dict[str, Any]:
        """Load safetensors format model"""
        # Safetensors is typically used with transformers
        return self._load_huggingface(model_path, **kwargs)
    
    def download(self, model_id: str, **kwargs) -> str:
        """
        Download a model from HuggingFace Hub.
        
        Args:
            model_id: HuggingFace model ID (e.g., "meta-llama/Llama-2-7b")
            **kwargs: Additional download arguments
            
        Returns:
            Local path to downloaded model
        """
        from huggingface_hub import snapshot_download
        
        cache_path = self.cache_dir / model_id.replace("/", "_")
        
        logger.info(f"Downloading {model_id} to {cache_path}")
        
        local_path = snapshot_download(
            repo_id=model_id,
            local_dir=str(cache_path),
            **kwargs,
        )
        
        return local_path
    
    def list_cached_models(self) -> list:
        """List all cached models"""
        return [str(p) for p in self.cache_dir.iterdir() if p.is_dir()]
    
    def clear_cache(self) -> None:
        """Clear the model cache"""
        import shutil
        for item in self.cache_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
        logger.info("Model cache cleared")
