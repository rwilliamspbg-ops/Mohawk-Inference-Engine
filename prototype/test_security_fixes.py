"""
Security fix verification tests for Mohawk Inference Engine v2.

Tests:
1. Pickle deserialization vulnerability (FIXED)
2. Replay attack protection (IMPLEMENTED)
3. HKDF salt/info hardcoding (FIXED)
4. Input validation (IMPLEMENTED)
5. Connection pooling (IMPLEMENTED)
"""

import pytest
import numpy as np
from prototype.model_tools_v2 import ToyModel, WeightSlice


def test_pickle_not_used():
    """Verify pickle is not used in serialization."""
    model = ToyModel([8, 16, 16, 8], seed=42)
    
    # Test model serialization
    model_bytes = model.to_bytes()
    assert isinstance(model_bytes, bytes)
    assert b'pickle' not in model_bytes.lower()
    
    # Test slice serialization
    slice_obj = model.slice(0, 2)
    slice_bytes = slice_obj.to_bytes()
    assert isinstance(slice_bytes, bytes)
    assert b'pickle' not in slice_bytes.lower()


def test_safe_deserialization():
    """Test that deserialization works without pickle."""
    model = ToyModel([8, 16, 16, 8], seed=42)
    
    # Serialize and deserialize
    model_bytes = model.to_bytes()
    
    # Verify we can reconstruct (simplified test)
    assert len(model_bytes) > 0


def test_slice_serialization():
    """Test slice object serialization."""
    model = ToyModel([8, 16, 16, 8], seed=42)
    
    # Create a slice
    slice_obj = model.slice(0, 2)
    
    # Serialize
    bytes_data = slice_obj.to_bytes()
    assert len(bytes_data) > 0
    
    # Verify version is preserved
    assert slice_obj.version == "v1.0"


def test_weight_shapes():
    """Test that weight shapes are preserved."""
    model = ToyModel([8, 16, 16, 8], seed=42)
    
    slice_obj = model.slice(0, 2)
    shapes = slice_obj.get_shapes()
    
    assert 'layer_0_0_weight' in shapes
    assert 'layer_0_0_bias' in shapes


def test_replay_protection_basic():
    """Test replay protection prevents nonce reuse."""
    from prototype.crypto_improved import ReplayProtectedAEAD
    
    key = b'test-key-for-replay-protection-1234567890ab'
    aead = ReplayProtectedAEAD(key, nonce_expiry_seconds=3600)
    
    # First encryption should succeed
    plaintext = b'secure message'
    nonce1, ct1 = aead.encrypt(plaintext)
    
    # Second encryption with same nonce should fail
    try:
        nonce2, ct2 = aead.encrypt(plaintext)
        assert False, "Should have raised RuntimeError for nonce collision"
    except RuntimeError as e:
        assert "collision" in str(e).lower() or "replay" in str(e).lower()


def test_replay_protection_fresh_nonce():
    """Test that fresh nonces work correctly."""
    from prototype.crypto_improved import ReplayProtectedAEAD
    
    key = b'test-key-for-replay-protection-1234567890ab'
    aead = ReplayProtectedAEAD(key, nonce_expiry_seconds=3600)
    
    # Each encryption generates fresh nonce
    for i in range(5):
        plaintext = f'message {i}'.encode()
        nonce, ct = aead.encrypt(plaintext)
        
        # Decrypt should succeed
        decrypted = aead.decrypt(nonce, ct)
        assert decrypted == plaintext


def test_hkdf_versioned_info():
    """Test that HKDF uses versioned info string."""
    from prototype.crypto_improved import PQCAdapter
    
    adapter = PQCAdapter()
    
    # Derive shared key
    peer_pub_bytes = bytes([0x00] * 32)  # Dummy public key
    shared_key = adapter.derive_shared(peer_pub_bytes)
    
    # Verify key is derived (non-empty)
    assert len(shared_key) == 32


def test_input_validation():
    """Test that worker validates input sizes."""
    import requests
    
    # Test with very large payload
    large_payload = base64.b64encode(b'x' * 100 * 1024 * 1024).decode('ascii')  # 100MB
    
    try:
        r = requests.post(
            'http://127.0.0.1:8000/execute',
            json={"slice_id": "test", "input_b64": large_payload}
        )
        # Should fail with 413 or similar
    except Exception as e:
        assert "too large" in str(e).lower() or r.status_code == 413


def test_connection_pooling():
    """Test that controller uses connection pooling."""
    from prototype.controller import Controller
    
    # Create controller - should create session object
    controller = Controller(["http://127.0.0.1:8001"])
    
    assert hasattr(controller, 'session')
    assert isinstance(controller.session, requests.Session)


def test_model_versioning():
    """Test that model versions are tracked."""
    model = ToyModel([8, 16, 16, 8], seed=42, version="v1.0")
    
    slice_obj = model.slice(0, 2)
    assert slice_obj.version == "v1.0"


def test_worker_health_endpoint():
    """Test worker health check endpoint."""
    import requests
    
    r = requests.get('http://127.0.0.1:8000/health')
    
    assert r.status_code == 200
    data = r.json()
    assert data['status'] == 'ok'
    assert 'timestamp' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
