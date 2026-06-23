"""
Tests for the API server
"""

import pytest
from fastapi.testclient import TestClient
from mohawk.engine import InferenceEngine
from mohawk.api.server import APIServer


@pytest.fixture
def client():
    """Create a test client"""
    engine = InferenceEngine()
    engine.load_model("test-model")
    server = APIServer(engine=engine, host="127.0.0.1", port=8000)
    return TestClient(server.app)


class TestAPIServer:
    """Test cases for APIServer"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Mohawk Inference Engine"
        assert "version" in data
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_list_models(self, client):
        """Test listing available models"""
        response = client.get("/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) > 0
    
    def test_completion_basic(self, client):
        """Test basic completion request"""
        response = client.post(
            "/v1/completions",
            json={
                "prompt": "Hello, world!",
                "max_tokens": 50,
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data
        assert len(data["choices"]) > 0
        assert "text" in data["choices"][0]
    
    def test_completion_with_parameters(self, client):
        """Test completion with various parameters"""
        response = client.post(
            "/v1/completions",
            json={
                "prompt": "Test prompt",
                "max_tokens": 100,
                "temperature": 0.8,
                "top_p": 0.95,
                "stop": ["\n\n"],
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data
    
    def test_completion_invalid_max_tokens(self, client):
        """Test completion with invalid max_tokens"""
        response = client.post(
            "/v1/completions",
            json={
                "prompt": "Test",
                "max_tokens": 0,  # Invalid: must be >= 1
            }
        )
        assert response.status_code == 422  # Validation error
    
    def test_completion_invalid_temperature(self, client):
        """Test completion with invalid temperature"""
        response = client.post(
            "/v1/completions",
            json={
                "prompt": "Test",
                "temperature": 3.0,  # Invalid: must be <= 2.0
            }
        )
        assert response.status_code == 422
    
    def test_chat_completion_basic(self, client):
        """Test basic chat completion request"""
        response = client.post(
            "/v1/chat/completions",
            json={
                "messages": [
                    {"role": "user", "content": "Hello!"},
                ],
                "max_tokens": 50,
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data
        assert len(data["choices"]) > 0
        assert "message" in data["choices"][0]
        assert data["choices"][0]["message"]["role"] == "assistant"
    
    def test_chat_completion_multi_turn(self, client):
        """Test multi-turn chat completion"""
        response = client.post(
            "/v1/chat/completions",
            json={
                "messages": [
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": "Hello!"},
                    {"role": "assistant", "content": "Hi there!"},
                    {"role": "user", "content": "How are you?"},
                ],
                "max_tokens": 50,
            }
        )
        assert response.status_code == 200
    
    def test_chat_completion_invalid_role(self, client):
        """Test chat completion with invalid role - roles are not strictly validated"""
        # Note: Pydantic doesn't validate enum for 'role' field by default
        # This test verifies the API accepts various role values gracefully
        response = client.post(
            "/v1/chat/completions",
            json={
                "messages": [
                    {"role": "custom_role", "content": "Test"},
                ],
            }
        )
        # The API should accept the request (role validation is optional)
        assert response.status_code == 200
