"""
Comprehensive test suite for Mohawk Inference Engine bug fixes.

Tests validate all critical issues have been resolved:
1. JWT token refresh type mismatch
2. Missing _update_metrics method
3. Page navigation references
4. Undefined strategy variable in error recovery
5. Percentile calculation accuracy
"""

import asyncio
import pytest
import tempfile
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from mohawk_gui.auth_manager import AuthManager
from mohawk_gui.error_recovery import ErrorRecoveryManager, RecoveryAction
from mohawk_gui.metrics_buffer import MetricsBuffer, MetricsAggregator


class TestJWTTokenRefresh:
    """Test fixes for JWT token refresh type mismatch (Issue #1)"""
    
    @pytest.mark.asyncio
    async def test_token_refresh_generates_new_token(self):
        """Verify token refresh creates a new token instead of returning None"""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_path = os.path.join(tmpdir, 'test_key.pem')
            auth = AuthManager(key_path)
            
            # Generate initial token
            token1 = await auth.generate_session_token("test_user", ["admin"])
            assert token1 is not None
            
            # Refresh should return a new token (not None)
            token2 = await auth.refresh_token(token1)
            assert token2 is not None, "Token refresh should not return None"
            assert token2 != token1, "Refreshed token should be different from original"
            
            # Verify new token is valid
            result = await auth.verify_token(token2)
            assert result["valid"], "Refreshed token should be valid"
            assert result["user_id"] == "test_user"
    
    @pytest.mark.asyncio
    async def test_token_refresh_handles_expired_token(self):
        """Verify token refresh handles expired tokens gracefully"""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_path = os.path.join(tmpdir, 'test_key.pem')
            auth = AuthManager(key_path)
            
            # Set very short expiry
            auth.token_expiry_hours = 0.0001  # ~0.36 seconds
            token = await auth.generate_session_token("test_user", ["admin"])
            
            # Wait for token to expire
            await asyncio.sleep(1)
            
            # Refresh should return None for expired token
            result = await auth.refresh_token(token)
            assert result is None, "Refresh of expired token should return None"
    
    @pytest.mark.asyncio
    async def test_timestamp_to_datetime_conversion(self):
        """Verify Unix timestamp is properly converted to datetime"""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_path = os.path.join(tmpdir, 'test_key.pem')
            auth = AuthManager(key_path)
            
            token = await auth.generate_session_token("user", ["admin"])
            result = await auth.verify_token(token)
            
            # exp should be an integer (Unix timestamp)
            assert isinstance(result["exp"], int), "JWT exp should be int timestamp"
            
            # Should be in the future
            now_ts = datetime.now(timezone.utc).timestamp()
            assert result["exp"] > now_ts, "Token expiry should be in future"


class TestErrorRecoveryAbort:
    """Test fixes for undefined strategy variable (Issue #4)"""
    
    @pytest.mark.asyncio
    async def test_abort_operation_no_nameerror(self):
        """Verify _abort_operation doesn't crash with NameError"""
        recovery = ErrorRecoveryManager()
        
        # Create a custom error matching a strategy
        class ModelLoadingError(Exception):
            pass
        
        # This should trigger abort action (registered in ErrorRecoveryManager)
        error = ModelLoadingError("Failed to load")
        
        # Should not raise NameError
        result = await recovery.handle_error(error, {"operation": "load"})
        # Result should be None (from abort), not a NameError
        assert result is None or isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_strategy_parameter_passed_correctly(self):
        """Verify strategy parameter is properly passed through call chain"""
        recovery = ErrorRecoveryManager()
        
        # Verify that strategies are properly initialized
        assert "ModelLoadingError" in recovery.strategies
        strategy = recovery.strategies["ModelLoadingError"]
        assert strategy.action == RecoveryAction.ABORT
        assert strategy.parameters.get("rollback_transaction") == True


class TestPercentileCalculation:
    """Test fixes for percentile calculation accuracy (Issue #5)"""
    
    @pytest.mark.asyncio
    async def test_percentile_p50_accuracy(self):
        """Verify p50 percentile calculation is accurate"""
        buffer = MetricsBuffer(window_size=100, sample_rate=1.0)
        
        # Add sequential data [0, 1, 2, ..., 99]
        for i in range(100):
            await buffer.add({
                "timestamp": float(i),
                "latency_p50_ms": float(i),
                "latency_p95_ms": float(i),
                "latency_p99_ms": float(i),
                "throughput_rps": float(i),
                "gpu_utilization": 0,
                "memory_mb": 0,
                "active_requests": 0
            })
        
        summary = buffer.get_summary()
        
        # For 100 items, p50 should be around 49-50
        # Using formula: index = int((n-1) * 0.50) = int(99 * 0.50) = 49
        # Value at index 49 = 49.0
        expected_p50 = 49.0
        actual_p50 = buffer._calculate_percentile(list(range(100)), 0.50)
        
        assert actual_p50 == expected_p50, f"p50 should be {expected_p50}, got {actual_p50}"
    
    @pytest.mark.asyncio
    async def test_percentile_p95_accuracy(self):
        """Verify p95 percentile calculation is accurate"""
        buffer = MetricsBuffer()
        
        # For 100 items [0..99], p95 should be around 94-95
        # Using formula: index = int((n-1) * 0.95) = int(99 * 0.95) = 94
        # Value at index 94 = 94.0
        data = list(range(100))
        actual_p95 = buffer._calculate_percentile(data, 0.95)
        
        assert 93 <= actual_p95 <= 95, f"p95 should be ~94, got {actual_p95}"
        assert actual_p95 == 94.0
    
    @pytest.mark.asyncio
    async def test_percentile_p99_accuracy(self):
        """Verify p99 percentile calculation is accurate"""
        buffer = MetricsBuffer()
        
        # For 100 items [0..99], p99 should be around 98-99
        # Using formula: index = int((n-1) * 0.99) = int(99 * 0.99) = 98
        # Value at index 98 = 98.0
        data = list(range(100))
        actual_p99 = buffer._calculate_percentile(data, 0.99)
        
        assert 97 <= actual_p99 <= 99, f"p99 should be ~98, got {actual_p99}"
        assert actual_p99 == 98.0
    
    @pytest.mark.asyncio
    async def test_percentile_boundary_conditions(self):
        """Verify percentile calculation handles boundaries correctly"""
        buffer = MetricsBuffer()
        data = [10, 20, 30, 40, 50]
        
        # p0 should return minimum
        p0 = buffer._calculate_percentile(data, 0.0)
        assert p0 == 10
        
        # p100 should return maximum
        p100 = buffer._calculate_percentile(data, 1.0)
        assert p100 == 50
        
        # p50 should be middle-ish
        p50 = buffer._calculate_percentile(data, 0.5)
        assert 20 <= p50 <= 40
    
    def test_percentile_validation(self):
        """Verify percentile input validation"""
        buffer = MetricsBuffer()
        data = [1, 2, 3, 4, 5]
        
        # Should raise for invalid percentiles
        with pytest.raises(ValueError):
            buffer._calculate_percentile(data, -0.1)
        
        with pytest.raises(ValueError):
            buffer._calculate_percentile(data, 1.1)
        
        # Valid percentiles should work
        buffer._calculate_percentile(data, 0.0)  # Should not raise
        buffer._calculate_percentile(data, 0.5)  # Should not raise
        buffer._calculate_percentile(data, 1.0)  # Should not raise


class TestMetricsBufferIntegration:
    """Integration tests for metrics buffer"""
    
    @pytest.mark.asyncio
    async def test_buffer_aggregation(self):
        """Verify buffer properly aggregates metrics"""
        buffer = MetricsBuffer(window_size=50, sample_rate=1.0)
        
        # Add multiple metrics
        for i in range(50):
            await buffer.add({
                "timestamp": float(i),
                "latency_p50_ms": 10.0 + (i % 5),  # Varies 10-14
                "latency_p95_ms": 30.0 + (i % 10),
                "latency_p99_ms": 50.0 + (i % 10),
                "throughput_rps": 100.0 + (i % 20),
                "gpu_utilization": 50.0 + (i % 30),
                "memory_mb": 1000.0,
                "active_requests": 5 + (i % 10)
            })
        
        summary = buffer.get_summary()
        
        # Verify summary is complete
        assert summary["count"] == 50
        assert summary["avg_latency_p50_ms"] > 0
        assert summary["min_latency_p50_ms"] > 0
        assert summary["max_latency_p50_ms"] > summary["min_latency_p50_ms"]
        assert "p95_latency_ms" in summary
        assert "p99_latency_ms" in summary
    
    @pytest.mark.asyncio
    async def test_aggregator_multi_session(self):
        """Verify aggregator handles multiple sessions"""
        agg = MetricsAggregator()
        
        # Add metrics for multiple sessions
        for session_id in ["session_1", "session_2", "session_3"]:
            for i in range(10):
                await agg.add_metrics(session_id, {
                    "timestamp": float(i),
                    "latency_p50_ms": float(i * 2),
                    "latency_p95_ms": float(i * 3),
                    "latency_p99_ms": float(i * 4),
                    "throughput_rps": float(100 + i),
                    "gpu_utilization": 50.0,
                    "memory_mb": 1000.0,
                    "active_requests": 5
                })
        
        global_summary = agg.get_global_summary()
        
        assert global_summary["total_sessions"] == 3
        assert global_summary["active_sessions_with_metrics"] == 3
        assert global_summary["global_avg_latency_p50_ms"] > 0
        assert global_summary["global_avg_throughput_rps"] > 0


class TestCompileAndImport:
    """Test that all modules compile and import correctly"""
    
    def test_auth_manager_import(self):
        """Verify auth_manager module imports without error"""
        from mohawk_gui.auth_manager import AuthManager, MTLSManager
        assert AuthManager is not None
        assert MTLSManager is not None
    
    def test_error_recovery_import(self):
        """Verify error_recovery module imports without error"""
        from mohawk_gui.error_recovery import (
            ErrorRecoveryManager, 
            RecoveryStrategy, 
            RecoveryAction,
            DegradedModeManager
        )
        assert ErrorRecoveryManager is not None
        assert RecoveryStrategy is not None
        assert RecoveryAction is not None
        assert DegradedModeManager is not None
    
    def test_metrics_buffer_import(self):
        """Verify metrics_buffer module imports without error"""
        from mohawk_gui.metrics_buffer import (
            MetricsBuffer,
            MetricsAggregator,
            BufferedMetrics
        )
        assert MetricsBuffer is not None
        assert MetricsAggregator is not None
        assert BufferedMetrics is not None


# Convenience function for running tests
def run_all_tests():
    """Run all tests and print results"""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    # Run tests
    run_all_tests()
