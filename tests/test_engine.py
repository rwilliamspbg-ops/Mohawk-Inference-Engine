"""
Tests for the InferenceEngine class
"""

import pytest
from mohawk.engine import InferenceEngine, InferenceResult


class TestInferenceEngine:
    """Test cases for InferenceEngine"""
    
    def test_init_default(self):
        """Test engine initialization with defaults"""
        engine = InferenceEngine()
        assert engine.device == "cpu"
        assert engine.model_path is None
        assert not engine.is_loaded
    
    def test_init_with_model_path(self):
        """Test engine initialization with model path"""
        engine = InferenceEngine(model_path="test-model")
        assert engine.model_path == "test-model"
        assert not engine.is_loaded
    
    def test_init_with_device(self):
        """Test engine initialization with custom device"""
        engine = InferenceEngine(device="cuda")
        assert engine.device == "cuda"
    
    def test_load_model(self):
        """Test model loading"""
        engine = InferenceEngine()
        engine.load_model("test-model-path")
        assert engine.is_loaded
        assert engine.model_path == "test-model-path"
    
    def test_unload_model(self):
        """Test model unloading"""
        engine = InferenceEngine()
        engine.load_model("test-model")
        assert engine.is_loaded
        
        engine.unload_model()
        assert not engine.is_loaded
    
    def test_generate_without_model(self):
        """Test that generate raises error without loaded model"""
        engine = InferenceEngine()
        with pytest.raises(RuntimeError, match="No model loaded"):
            engine.generate("test prompt")
    
    def test_generate_basic(self):
        """Test basic text generation"""
        engine = InferenceEngine()
        engine.load_model("test-model")
        
        result = engine.generate("Hello, world!", max_tokens=50)
        
        assert isinstance(result, InferenceResult)
        assert result.text is not None
        assert result.tokens_generated >= 0
        assert result.latency_ms >= 0
        assert result.model_name == "test-model"
    
    def test_generate_with_parameters(self):
        """Test generation with various parameters"""
        engine = InferenceEngine()
        engine.load_model("test-model")
        
        result = engine.generate(
            "Test prompt",
            max_tokens=100,
            temperature=0.8,
            top_p=0.95,
            stop_sequences=["\n\n"],
        )
        
        assert isinstance(result, InferenceResult)
    
    def test_stream_generate(self):
        """Test streaming generation"""
        engine = InferenceEngine()
        engine.load_model("test-model")
        
        generator = engine.generate(
            "Test prompt",
            max_tokens=5,
            stream=True,
        )
        
        # Should return a generator
        assert hasattr(generator, "__iter__")
        assert hasattr(generator, "__next__")
        
        # Consume the generator
        tokens = list(generator)
        assert len(tokens) > 0
    
    def test_get_info(self):
        """Test getting engine information"""
        engine = InferenceEngine(device="mps")
        engine.load_model("my-model")
        
        info = engine.get_info()
        
        assert info["model_loaded"] is True
        assert info["model_path"] == "my-model"
        assert info["device"] == "mps"
        assert "version" in info
    
    def test_get_info_no_model(self):
        """Test getting engine info without loaded model"""
        engine = InferenceEngine()
        
        info = engine.get_info()
        
        assert info["model_loaded"] is False
        assert info["model_path"] is None
