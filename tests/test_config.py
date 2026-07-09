"""
Tests for configuration utilities
"""

import pytest
import json
from pathlib import Path
from mohawk.utils.config import Config


class TestConfig:
    """Test cases for Config"""
    
    def test_default_values(self):
        """Test default configuration values"""
        config = Config()
        assert config.host == "0.0.0.0"
        assert config.port == 8080
        assert config.model_path is None
        assert config.default_max_tokens == 512
        assert config.default_temperature == 0.7
        assert config.num_threads == 4
    
    def test_from_env(self, monkeypatch):
        """Test loading config from environment variables"""
        monkeypatch.setenv("MOHAWK_HOST", "localhost")
        monkeypatch.setenv("MOHAWK_PORT", "9000")
        monkeypatch.setenv("MOHAWK_LOG_LEVEL", "DEBUG")
        
        config = Config.from_env()
        
        assert config.host == "localhost"
        assert config.port == 9000
        assert config.log_level == "DEBUG"
    
    def test_from_dict(self):
        """Test loading config from dictionary"""
        data = {
            "host": "127.0.0.1",
            "port": 3000,
            "log_level": "WARNING",
        }
        
        config = Config.from_dict(data)
        
        assert config.host == "127.0.0.1"
        assert config.port == 3000
        assert config.log_level == "WARNING"
    
    def test_to_dict(self):
        """Test converting config to dictionary"""
        config = Config(host="localhost", port=9999)
        data = config.to_dict()
        
        assert data["host"] == "localhost"
        assert data["port"] == 9999
        assert isinstance(data, dict)
    
    def test_save_and_load(self, tmp_path):
        """Test saving and loading config from file"""
        config_path = tmp_path / "config.json"
        
        # Create and save config
        original = Config(host="test-host", port=1234, log_level="ERROR")
        original.save(str(config_path))
        
        # Load config
        loaded = Config.load(str(config_path))
        
        assert loaded.host == original.host
        assert loaded.port == original.port
        assert loaded.log_level == original.log_level
    
    def test_save_creates_file(self, tmp_path):
        """Test that save creates the config file"""
        config_path = tmp_path / "config.json"
        config = Config()
        config.save(str(config_path))
        
        assert config_path.exists()
        
        # Verify it's valid JSON
        with open(config_path) as f:
            data = json.load(f)
        assert "host" in data
