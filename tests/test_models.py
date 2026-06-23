"""
Tests for the ModelLoader class
"""

import pytest
from pathlib import Path
from mohawk.models.loader import ModelLoader, ModelFormat


class TestModelLoader:
    """Test cases for ModelLoader"""
    
    def test_init_default(self):
        """Test loader initialization with defaults"""
        loader = ModelLoader()
        assert loader.cache_dir.exists()
        assert "mohawk" in str(loader.cache_dir)
    
    def test_init_with_cache_dir(self, tmp_path):
        """Test loader initialization with custom cache dir"""
        loader = ModelLoader(cache_dir=str(tmp_path))
        assert loader.cache_dir == tmp_path
    
    def test_detect_format_gguf(self):
        """Test GGUF format detection"""
        loader = ModelLoader()
        fmt = loader.detect_format("model.gguf")
        assert fmt == ModelFormat.GGUF
    
    def test_detect_format_onnx(self):
        """Test ONNX format detection"""
        loader = ModelLoader()
        fmt = loader.detect_format("model.onnx")
        assert fmt == ModelFormat.ONNX
    
    def test_detect_format_huggingface_id(self):
        """Test HuggingFace model ID detection"""
        loader = ModelLoader()
        fmt = loader.detect_format("meta-llama/Llama-2-7b")
        assert fmt == ModelFormat.HUGGINGFACE
    
    def test_detect_format_safetensors(self, tmp_path):
        """Test safetensors format detection"""
        loader = ModelLoader()
        
        # Create a directory with safetensors file
        model_dir = tmp_path / "model"
        model_dir.mkdir()
        (model_dir / "model.safetensors").touch()
        
        fmt = loader.detect_format(str(model_dir))
        assert fmt == ModelFormat.SAFETENSORS
    
    def test_load_invalid_format(self):
        """Test loading with unsupported format"""
        loader = ModelLoader()
        
        # Test with an invalid format enum
        from unittest.mock import patch, MagicMock
        
        # Create a mock that returns None for detect_format
        with patch.object(loader, 'detect_format', return_value=None):
            with pytest.raises((ValueError, AttributeError)):
                loader.load("fake-model")
    
    def test_list_cached_models_empty(self, tmp_path):
        """Test listing cached models when empty"""
        loader = ModelLoader(cache_dir=str(tmp_path))
        models = loader.list_cached_models()
        assert len(models) == 0
    
    def test_list_cached_models_with_content(self, tmp_path):
        """Test listing cached models with content"""
        loader = ModelLoader(cache_dir=str(tmp_path))
        
        # Create some model directories
        (tmp_path / "model1").mkdir()
        (tmp_path / "model2").mkdir()
        (tmp_path / "file.txt").touch()  # Should be ignored
        
        models = loader.list_cached_models()
        assert len(models) == 2
    
    def test_clear_cache(self, tmp_path):
        """Test clearing the cache"""
        loader = ModelLoader(cache_dir=str(tmp_path))
        
        # Add some content
        (tmp_path / "model1").mkdir()
        (tmp_path / "model2").mkdir()
        
        loader.clear_cache()
        
        # Cache should be empty
        assert len(list(tmp_path.iterdir())) == 0

    def test_add_local_model_registers_library_entry(self, tmp_path):
        """Adding local models should persist an index entry."""
        loader = ModelLoader(cache_dir=str(tmp_path))
        local_model = tmp_path / "my_local_model"
        local_model.mkdir()

        entry = loader.add_local_model(str(local_model), alias="my-model")

        assert entry["model_id"] == "my-model"
        assert entry["source"] == "local"
        assert entry["local_path"] == str(local_model)
        assert any(item["model_id"] == "my-model" for item in loader.list_library())

    def test_download_registers_huggingface_model(self, tmp_path, monkeypatch):
        """Downloaded HF models should be added to the model library."""
        loader = ModelLoader(cache_dir=str(tmp_path))

        captured = {}

        def fake_snapshot_download(repo_id, **kwargs):
            captured["repo_id"] = repo_id
            captured["kwargs"] = kwargs
            target = Path(kwargs["local_dir"])
            target.mkdir(parents=True, exist_ok=True)
            (target / "config.json").write_text("{}", encoding="utf-8")
            return str(target)

        monkeypatch.setattr("huggingface_hub.snapshot_download", fake_snapshot_download)

        out_path = loader.download("org/model-a")

        assert captured["repo_id"] == "org/model-a"
        assert Path(out_path).exists()
        assert Path(captured["kwargs"]["local_dir"]).name == "org--model-a"
        assert any(item["model_id"] == "org/model-a" for item in loader.list_library())

    def test_download_rejects_empty_model_id(self, tmp_path):
        """Invalid/blank model IDs should fail early."""
        loader = ModelLoader(cache_dir=str(tmp_path))

        with pytest.raises(ValueError):
            loader.download("   ")
