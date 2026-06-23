# Troubleshooting Guide for Mohawk Inference Engine

This guide covers common issues and their resolutions.

## Table of Contents

- [Connection Issues](#connection-issues)
- [Handshake Failures](#handshake-failures)
- [Slice Loading Errors](#slice-loading-errors)
- [Performance Degradation](#performance-degradation)
- [Memory Issues](#memory-issues)
- [PQC/LibOQS Errors](#pqcliboqs-errors)
- [Telemetry/Metrics Problems](#telemetrymetrics-problems)
- [Security/Encryption Errors](#securityencryption-errors)

---

## Connection Issues

### Error: `Connection refused` or `Timeout`

**Symptoms:**
```
requests.exceptions.ConnectionError: Connection refused
requests.exceptions.Timeout: Request timed out
```

**Possible Causes:**
1. Worker not started or crashed
2. Firewall blocking port
3. Network partition in cluster

**Resolution Steps:**

1. **Check worker status:**
   ```bash
   curl http://localhost:8003/metrics
   # Should return metrics JSON, not connection refused
   ```

2. **Verify network connectivity:**
   ```bash
   telnet <worker-host> 8003
   # Or: nc -zv <worker-host> 8003
   ```

3. **Check firewall rules:**
   ```bash
   # On Linux
   sudo ufw status
   sudo iptables -L -n | grep 8003
   
   # Allow traffic
   sudo ufw allow 8003/tcp
   ```

4. **Restart worker with health check:**
   ```bash
   python prototype/worker_secure.py --port 8003 --health-check-enabled true
   ```

---

## Handshake Failures

### Error: `Handshake failed` or `Invalid AEAD key`

**Symptoms:**
```json
{
  "status": 400,
  "detail": "invalid AEAD key for this session"
}
```

**Possible Causes:**
1. X25519 key exchange mismatch
2. Replay attack detected (nonce reuse)
3. Certificate validation failed
4. PQC KEM extension incompatible

**Resolution Steps:**

1. **Verify handshake request format:**
   ```json
   {
     "client_pub_b64": "<base64-encoded-X25519-pubkey>",
     "oqs_pub_b64": "<optional: base64-encoded-Kyber-pubkey>"
   }
   ```

2. **Check liboqs availability:**
   ```python
   from prototype.crypto import OQS_AVAILABLE
   print(OQS_AVAILABLE)  # Should be True for PQC mode
   
   if not OQS_AVAILABLE:
       # Install liboqs
       import subprocess
       subprocess.run(['sudo', 'apt-get', 'install', '-y', 'liboqs'])
   ```

3. **Verify nonce freshness (replay protection):**
   ```bash
   # Check controller nonce tracking
   python -c "
   from prototype.crypto import PQCAdapter
   c = PQCAdapter()
   print('Nonce expiry:', 3600, 'seconds')
   "
   ```

4. **Reset session if keys corrupted:**
   ```python
   # In controller_secure.py
   def reset_worker_handshake(self, worker_url):
       """Force new handshake with worker."""
       self.keys.pop(worker_url, None)
       self.kems.pop(worker_url, None)
       self.handshake_with_worker(worker_url)
   ```

---

## Slice Loading Errors

### Error: `slice not found` (404)

**Symptoms:**
```json
{
  "status": 404,
  "detail": "slice not found"
}
```

**Possible Causes:**
1. Slice preload failed silently
2. Worker restarted after slice loaded
3. Model partitioning mismatch

**Resolution Steps:**

1. **Verify slice preloading:**
   ```bash
   # Check worker metrics for preload failures
   curl http://localhost:8003/metrics | grep -i preload
   ```

2. **Manual slice preload test:**
   ```python
   import requests
   
   payload = {
       "slice_id": "slice_0_4",
       "manifest": {"start": 0, "end": 4},
       "weights_b64": "<base64-encoded-weights>",
       "encrypted": False
   }
   
   resp = requests.post("http://localhost:8003/preload", json=payload)
   print(resp.json())  # Should return {"status": "ok", ...}
   ```

3. **Check worker logs for deserialization errors:**
   ```bash
   tail -f /var/log/mohawk/worker.log | grep -i "deserialize\|pickle"
   ```

4. **Restart worker after model update:**
   ```bash
   # Stop and restart worker
   systemctl stop mohawk-worker
   python prototype/worker_secure.py --port 8003
   systemctl start mohawk-worker
   ```

---

## Performance Degradation

### Symptom: High Latency (>500ms per inference)

**Possible Causes:**
1. Memory pressure causing swapping
2. Network bottleneck between workers
3. CPU throttling due to thermal limits
4. GC overhead in Python

**Resolution Steps:**

1. **Check memory usage:**
   ```bash
   # On worker node
   free -h
   vmstat 1 5
   
   # Check for swapping (should be 0)
   cat /proc/meminfo | grep Swap
   ```

2. **Enable hugepages:**
   ```bash
   echo "vm.nr_hugepages = 16384" >> /etc/sysctl.conf
   sysctl -p
   
   # Verify hugepages allocated
   cat /proc/meminfo | grep HugePages_Total
   ```

3. **Check CPU frequency scaling:**
   ```bash
   # On CPU workers, set performance governor
   sudo cpufreq-set -g performance
   
   # Or pin to specific cores
   taskset -c 0-7 python prototype/worker_secure.py --port 8003
   ```

4. **Monitor GC overhead:**
   ```python
   import gc
   import tracemalloc
   
   tracemalloc.start()
   
   # Run inference loop
   for i in range(100):
       result = model.infer(x)
   
   current, peak = tracemalloc.get_traced_memory()
   print(f"Current memory: {current / 10**6:.2f} MB")
   print(f"Peak memory: {peak / 10**6:.2f} MB")
   ```

---

## Memory Issues

### Error: `MemoryError` or Out-of-Memory Kill (OOM)

**Symptoms:**
```
fatal error: allocating ... bytes
Killed
```

**Possible Causes:**
1. Model weights exceed available memory
2. Activation buffer too large for device
3. Not enough hugepages configured

**Resolution Steps:**

1. **Check model size vs available memory:**
   ```python
   import numpy as np
   
   # Calculate model weight size
   layer_sizes = [8, 16, 16, 8]
   total_params = sum(np.prod((l_i+1, l_{i+1})) for i in range(len(layer_sizes)-1))
   print(f"Total parameters: {total_params}")
   print(f"Memory footprint (float32): {total_params * 4 / 1024**2:.2f} MB")
   ```

2. **Reduce model size or increase memory:**
   ```python
   # Option 1: Use quantization (int8)
   from prototype.quantize import quantize_weights
   
   quantized_model = quantize_weights(model, bits=8)
   
   # Option 2: Reduce layer sizes
   model = ToyModel([4,8,8,4], seed=42)  # Smaller than [8,16,16,8]
   ```

3. **Configure hugepages for worker:**
   ```bash
   # Add to /etc/sysctl.conf
   vm.nr_hugepages = 16384
   
   # Or dynamically (requires root)
   sudo sysctl -w vm.nr_hugepages=16384
   ```

---

## PQC/LibOQS Errors

### Error: `OQS not available` or `pyOQS KEM API not available`

**Symptoms:**
```
RuntimeError: OQS not available
pytest.skip('oqs module not available')
```

**Possible Causes:**
1. liboqs not installed on system
2. OQS_INSTALL_PATH not set correctly
3. pyOQS Python binding missing

**Resolution Steps:**

1. **Install liboqs (Ubuntu/Debian):**
   ```bash
   sudo apt-get update
   sudo apt-get install -y build-essential cmake libssl-dev pkg-config
   
   # Build and install liboqs from source
   git clone --branch main https://github.com/open-quantum-safe/liboqs.git
   cd liboqs
   mkdir build && cd build
   cmake -DCMAKE_INSTALL_PREFIX=/usr/local ..
   make -j$(nproc)
   sudo make install
   sudo ldconfig
   ```

2. **Install Python binding:**
   ```bash
   pip install liboqs-python
   
   # Verify installation
   python -c "import oqs; print('liboqs available:', oqs.__version__)"
   ```

3. **Set environment variable:**
   ```bash
   export OQS_INSTALL_PATH=/usr/local
   
   # Or add to ~/.bashrc or Dockerfile
   echo 'export OQS_INSTALL_PATH=/usr/local' >> ~/.bashrc
   source ~/.bashrc
   ```

4. **Verify PQC support in application:**
   ```python
   from prototype.crypto import OQS_AVAILABLE
   print("OQS Available:", OQS_AVAILABLE)
   
   if OQS_AVAILABLE:
       adapter = PQCAdapter('Kyber768')
       print("PQC Algorithm:", adapter.oqs_alg)
   ```

---

## Telemetry/Metrics Problems

### Error: Missing metrics or `/metrics` endpoint returns 500

**Possible Causes:**
1. Metrics collection not enabled
2. Prometheus exporter not running
3. Histogram computation overflow

**Resolution Steps:**

1. **Verify metrics endpoint is responding:**
   ```bash
   curl http://localhost:8003/metrics
   
   # Should return Prometheus-format metrics like:
   # handshakes_total 12
   # preload_time_sum 45.67
   # preload_time_count 12
   ```

2. **Enable telemetry in worker:**
   ```python
   # Add to worker_secure.py if not present
   from prototype.telemetry import Telemetry
   
   # Initialize with metrics dict and lock
   metrics = {
       'handshakes': 0,
       'preload_success': 0,
       'preload_fail': 0,
       'execute_success': 0,
       'execute_fail': 0,
   }
   metrics_lock = threading.Lock()
   
   telemetry = Telemetry(metrics, metrics_lock)
   ```

3. **Check for metric name collisions:**
   ```python
   # Ensure unique metric names
   valid_metric_names = [
       'handshakes_total',
       'preload_time_sum',
       'preload_time_count',
       'execute_time_sum',
       'execute_time_count',
   ]
   
   # Validate before recording
   def record_metric(name, value):
       if name not in valid_metric_names:
           raise ValueError(f"Invalid metric name: {name}")
   ```

---

## Security/Encryption Errors

### Error: `ReplayError` or `Nonce already seen`

**Symptoms:**
```
ReplayError: Nonce <nonce-hex> is stale
```

**Possible Causes:**
1. Client sending replayed messages
2. Nonce expired (window too old)
3. Clock skew between controller and worker

**Resolution Steps:**

1. **Verify time synchronization:**
   ```bash
   # On all cluster nodes
   chronyc -a makestep
   # Or: ntpq -p
   
   # Verify clocks are synchronized
   date
   ```

2. **Increase nonce expiry window (temporary workaround):**
   ```python
   # In controller_secure.py, modify ReplayProtectedAEAD
   class ReplayProtectedAEAD(AEAD):
       def __init__(self, key: bytes, expected_sender_id: str, 
                    nonce_expiry_seconds: int = 7200):  # Changed from 3600 to 7200
           super().__init__(key)
           self.nonce_expiry = nonce_expiry_seconds
   ```

3. **Clear nonce cache if compromised:**
   ```python
   # On controller side
   def clear_nonce_cache(self, sender_id: str):
       """Clear cached nonces for this sender."""
       if sender_id in self.seen_nonces:
           del self.seen_nonces[sender_id]
   ```

---

## Debug Mode Configuration

### Enable verbose logging

Add to worker/controller startup:

```bash
# Verbose mode
python prototype/worker_secure.py --port 8003 --verbose true --debug-logging

# Or set environment variable
export DEBUG=true
export LOG_LEVEL=DEBUG
```

### Modify logging configuration

Create `logging_config.json`:

```json
{
  "version": 1,
  "disable_existing_loggers": false,
  "formatters": {
    "detailed": {
      "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
      "datefmt": "%Y-%m-%d %H:%M:%S"
    }
  },
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "formatter": "detailed",
      "level": "INFO"
    },
    "file": {
      "class": "logging.FileHandler",
      "filename": "/var/log/mohawk/worker.log",
      "formatter": "detailed",
      "level": "DEBUG"
    }
  },
  "loggers": {
    "prototype": {
      "handlers": ["console", "file"],
      "level": "DEBUG"
    }
  }
}
```

---

## Quick Reference: Common Commands

```bash
# Restart all workers
systemctl restart mohawk-worker@worker-1
systemctl restart mohawk-worker@worker-2
systemctl restart mohawk-worker@worker-3

# Check cluster health
for worker in worker-1 worker-2 worker-3; do
  echo "=== $worker ==="
  curl -s http://localhost:8003/metrics | head -20
done

# Clear all session state (development only!)
python -c "
from prototype.worker_secure import slices, keys, metrics, metrics_lock
slices.clear()
keys.clear()
with metrics_lock:
    for k in metrics:
        metrics[k] = 0
"

# Generate new test data with different seeds
python prototype/run_demo.py --seed 12345

# Run single session with verbose output
python prototype/test_secure_run.py --verbose true

# Check Prometheus metrics aggregation
curl http://localhost:9090/graph?g0.expr=rate%28mohawk_inferences_total%5B1m%5D%29
```

---

## Escalation Path

| Issue Type | Contact | SLA |
|------------|---------|-----|
| **Critical Outage** | #mohawk-critical-oncall | < 15 min response |
| **Security Incident** | security@mohawk.internal | Immediate |
| **Performance Regression** | mohawk-ops@sovereign-mohawk-proto.io | < 4 hours |
| **Feature Request** | GitHub Issues | Standard backlog |

---

## Related Documentation

- [SECURITY.md](./SECURITY.md) - Security hardening procedures
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Production deployment patterns
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System design overview

---

*Last updated: 2026-01-XX*
*Maintained by: Mohawk Ops Team, Sovereign Mohawk Proto LLC*
