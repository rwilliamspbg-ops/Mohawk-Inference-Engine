#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mohawk Inference Engine - Comprehensive Test Suite
Tests all user-facing functions for issues
"""

import requests
import json
import time
import sys
from typing import Dict, List, Any, Tuple
from datetime import datetime

# Force UTF-8 encoding
if sys.platform == "win32":
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Configuration
GUI_URL = "http://localhost:8003"
WORKER_URL = "http://localhost:8004"
TIMEOUT = 10

# Color codes for output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


class TestResult:
    """Holds test result information."""
    
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error = None
        self.response = None
        self.duration = 0.0
    
    def __str__(self):
        status = "[PASS]" if self.passed else "[FAIL]"
        status_color = GREEN if self.passed else RED
        result = f"{status_color}{status}{RESET} | {self.name:50} | {self.duration:.3f}s"
        if self.error:
            result += f"\n     {RED}Error: {self.error}{RESET}"
        return result


class MohawkTestSuite:
    """Comprehensive test suite for Mohawk Inference Engine."""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.session = requests.Session()
    
    def test(self, name: str, method: str, url: str, expect_error: bool = False, **kwargs) -> TestResult:
        """Execute a test request."""
        result = TestResult(name)
        start = time.time()
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, timeout=TIMEOUT, **kwargs)
            elif method.upper() == "POST":
                response = self.session.post(url, timeout=TIMEOUT, **kwargs)
            else:
                result.error = f"Unknown method: {method}"
                return result
            
            result.response = response
            
            # If we expect an error, 4xx/5xx is success
            if expect_error:
                result.passed = response.status_code >= 400
                if not result.passed:
                    result.error = f"Expected error but got HTTP {response.status_code}"
            else:
                result.passed = response.status_code < 400
                if not result.passed:
                    result.error = f"HTTP {response.status_code}: {response.text[:100]}"
        
        except requests.Timeout:
            result.error = "Request timeout"
        except requests.ConnectionError:
            result.error = "Connection error"
        except Exception as e:
            result.error = str(e)
        
        finally:
            result.duration = time.time() - start
            self.results.append(result)
        
        return result
    
    def print_results(self):
        """Print formatted test results."""
        print("\n" + "=" * 120)
        print(f"{BOLD}MOHAWK INFERENCE ENGINE - TEST RESULTS{RESET}")
        print("=" * 120)
        
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        pct = (passed / total * 100) if total > 0 else 0
        
        for result in self.results:
            print(result)
        
        print("\n" + "=" * 120)
        status_color = GREEN if pct == 100 else YELLOW if pct >= 80 else RED
        print(f"{BOLD}SUMMARY: {status_color}{passed}/{total} passed ({pct:.1f}%){RESET}")
        print("=" * 120 + "\n")
        
        return pct == 100


# ============================================================================
# TEST SUITE DEFINITIONS
# ============================================================================

def test_health_checks(suite: MohawkTestSuite):
    """Test basic health check endpoints."""
    print(f"\n{BOLD}{BLUE}[1] HEALTH CHECKS{RESET}")
    
    suite.test(
        "GUI health check",
        "GET", f"{GUI_URL}/health"
    )
    
    suite.test(
        "Worker health check",
        "GET", f"{WORKER_URL}/health"
    )
    
    suite.test(
        "GUI API health",
        "GET", f"{GUI_URL}/api/health"
    )


def test_models(suite: MohawkTestSuite):
    """Test model management endpoints."""
    print(f"\n{BOLD}{BLUE}[2] MODEL MANAGEMENT{RESET}")
    
    # List models
    result = suite.test(
        "List available models",
        "GET", f"{GUI_URL}/api/models"
    )
    
    if result.passed and result.response:
        models = result.response.json().get("models", [])
        print(f"   Found {len(models)} models")
        for model in models:
            print(f"     - {model['name']} ({model['size_gb']}GB)")
    
    # Load model
    suite.test(
        "Load model (Llama-3-8B)",
        "POST", f"{GUI_URL}/api/models/load",
        json={"model": "Llama-3-8B-Instruct-Q4_K_M"}
    )


def test_inference(suite: MohawkTestSuite):
    """Test inference/chat endpoints."""
    print(f"\n{BOLD}{BLUE}[3] INFERENCE & CHAT{RESET}")
    
    test_messages = [
        "Hello, how are you?",
        "What is 2+2?",
        "Explain machine learning briefly",
    ]
    
    for i, msg in enumerate(test_messages, 1):
        suite.test(
            f"Chat inference ({i}/3): '{msg[:30]}...'",
            "POST", f"{GUI_URL}/api/inference/chat",
            json={
                "message": msg,
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 2048,
                "system_prompt": "You are a helpful AI assistant."
            }
        )


def test_metrics(suite: MohawkTestSuite):
    """Test metrics endpoints."""
    print(f"\n{BOLD}{BLUE}[4] METRICS & MONITORING{RESET}")
    
    # Get metrics
    result = suite.test(
        "Get current metrics",
        "GET", f"{GUI_URL}/api/metrics"
    )
    
    if result.passed and result.response:
        metrics = result.response.json()
        print(f"   CPU: {metrics.get('cpu', 0):.1f}%")
        print(f"   Memory: {metrics.get('memory', 0):.1f}%")
        print(f"   GPU: {metrics.get('gpu', 0):.1f}%")
        print(f"   Throughput: {metrics.get('throughput', 0)} tokens/s")
        print(f"   Requests: {metrics.get('total_requests', 0)}")
    
    # Update metrics
    suite.test(
        "Update metrics",
        "POST", f"{GUI_URL}/api/metrics/update",
        json={"cpu": 45, "memory": 62}
    )


def test_workers(suite: MohawkTestSuite):
    """Test worker management endpoints."""
    print(f"\n{BOLD}{BLUE}[5] WORKER MANAGEMENT{RESET}")
    
    # List workers
    result = suite.test(
        "List connected workers",
        "GET", f"{GUI_URL}/api/workers"
    )
    
    if result.passed and result.response:
        data = result.response.json()
        workers = data.get("workers", [])
        print(f"   Found {len(workers)} workers")
        for w in workers:
            print(f"     - {w['id']} ({w['status']}) on port {w['port']}")
    
    # Connect to workers
    suite.test(
        "Connect to workers",
        "POST", f"{GUI_URL}/api/workers/connect"
    )


def test_sessions(suite: MohawkTestSuite):
    """Test session management."""
    print(f"\n{BOLD}{BLUE}[6] SESSION MANAGEMENT{RESET}")
    
    # Create session
    result = suite.test(
        "Create inference session",
        "POST", f"{GUI_URL}/api/sessions/create",
        json={}
    )
    
    session_id = None
    if result.passed and result.response:
        session_data = result.response.json()
        session_id = session_data.get("session_id")
        print(f"   Created session: {session_id}")
    
    # List sessions
    result = suite.test(
        "List active sessions",
        "GET", f"{GUI_URL}/api/sessions"
    )
    
    if result.passed and result.response:
        sessions = result.response.json().get("sessions", [])
        print(f"   {len(sessions)} active sessions")
    
    # Cancel session (if we created one)
    if session_id:
        suite.test(
            f"Cancel session {session_id}",
            "POST", f"{GUI_URL}/api/sessions/{session_id}/cancel"
        )


def test_job_queue(suite: MohawkTestSuite):
    """Test job queueing."""
    print(f"\n{BOLD}{BLUE}[7] JOB QUEUEING{RESET}")
    
    priorities = ["low", "normal", "high"]
    
    for priority in priorities:
        suite.test(
            f"Queue job with priority: {priority}",
            "POST", f"{GUI_URL}/api/queue",
            json={"priority": priority}
        )


def test_security(suite: MohawkTestSuite):
    """Test security endpoints."""
    print(f"\n{BOLD}{BLUE}[8] SECURITY & CRYPTOGRAPHY{RESET}")
    
    # JWT refresh
    suite.test(
        "Refresh JWT token",
        "POST", f"{GUI_URL}/api/security/jwt/refresh"
    )
    
    # PQC enable
    suite.test(
        "Enable Post-Quantum Cryptography",
        "POST", f"{GUI_URL}/api/security/pqc/enable"
    )


def test_discovery(suite: MohawkTestSuite):
    """Test LAN service discovery."""
    print(f"\n{BOLD}{BLUE}[9] LAN SERVICE DISCOVERY{RESET}")
    
    # Get discovery status
    result = suite.test(
        "Get discovery status",
        "GET", f"{GUI_URL}/api/discovery/status"
    )
    
    if result.passed and result.response:
        status = result.response.json()
        print(f"   Discovery enabled: {status.get('discovery_enabled', False)}")
        print(f"   Local IP: {status.get('local_ip', 'N/A')}")
        print(f"   Services found: {status.get('services_found', 0)}")
    
    # List discovered services
    suite.test(
        "List discovered services",
        "GET", f"{GUI_URL}/api/discovery/services"
    )
    
    # List GUI services
    suite.test(
        "List discovered GUI services",
        "GET", f"{GUI_URL}/api/discovery/gui"
    )
    
    # List worker services
    suite.test(
        "List discovered worker services",
        "GET", f"{GUI_URL}/api/discovery/workers"
    )
    
    # Refresh discovery
    suite.test(
        "Refresh service discovery",
        "POST", f"{GUI_URL}/api/discovery/refresh"
    )


def test_root_endpoints(suite: MohawkTestSuite):
    """Test root and info endpoints."""
    print(f"\n{BOLD}{BLUE}[10] ROOT & INFO ENDPOINTS{RESET}")
    
    result = suite.test(
        "GUI root endpoint",
        "GET", f"{GUI_URL}/"
    )
    
    if result.passed and result.response:
        info = result.response.json()
        print(f"   Service: {info.get('service', 'Unknown')}")
        print(f"   Version: {info.get('version', 'Unknown')}")
        print(f"   Status: {info.get('status', 'Unknown')}")


def test_error_handling(suite: MohawkTestSuite):
    """Test error handling for invalid requests."""
    print(f"\n{BOLD}{BLUE}[11] ERROR HANDLING{RESET}")
    
    # Invalid endpoint (should 404)
    suite.test(
        "Invalid endpoint returns 404",
        "GET", f"{GUI_URL}/api/nonexistent",
        expect_error=True
    )
    
    # Invalid session ID (should 404)
    suite.test(
        "Cancel nonexistent session returns 404",
        "POST", f"{GUI_URL}/api/sessions/invalid_session_id/cancel",
        expect_error=True
    )


def test_performance(suite: MohawkTestSuite):
    """Test performance and response times."""
    print(f"\n{BOLD}{BLUE}[12] PERFORMANCE & LATENCY{RESET}")
    
    # Quick health check (baseline)
    for i in range(5):
        suite.test(
            f"Health check latency ({i+1}/5)",
            "GET", f"{GUI_URL}/health"
        )
    
    # Analyze latencies
    latencies = [r.duration for r in suite.results[-5:] if r.passed]
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        print(f"   Min: {min_latency*1000:.2f}ms | Avg: {avg_latency*1000:.2f}ms | Max: {max_latency*1000:.2f}ms")


def main():
    """Run full test suite."""
    print(f"\n{BOLD}{BLUE}{'='*120}")
    print(f"MOHAWK INFERENCE ENGINE - COMPREHENSIVE USER FUNCTION TEST")
    print(f"{'='*120}{RESET}\n")
    
    print(f"{YELLOW}GUI Server: {GUI_URL}{RESET}")
    print(f"{YELLOW}Worker Server: {WORKER_URL}{RESET}")
    print(f"{YELLOW}Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}\n")
    
    suite = MohawkTestSuite()
    
    # Verify services are up
    try:
        requests.get(f"{GUI_URL}/health", timeout=5)
        requests.get(f"{WORKER_URL}/health", timeout=5)
    except Exception as e:
        print(f"{RED}ERROR: Services not running: {e}{RESET}")
        return False
    
    # Run all test categories
    test_health_checks(suite)
    test_root_endpoints(suite)
    test_models(suite)
    test_inference(suite)
    test_metrics(suite)
    test_workers(suite)
    test_sessions(suite)
    test_job_queue(suite)
    test_security(suite)
    test_discovery(suite)
    test_error_handling(suite)
    test_performance(suite)
    
    # Print results
    return suite.print_results()


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
