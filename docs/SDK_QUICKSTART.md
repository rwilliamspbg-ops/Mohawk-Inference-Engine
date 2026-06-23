# Mohawk Inference Engine SDK - Quick Start Guide

## Installation

### Using pip

```bash
pip install mohawk-sdk
```

### From Source

```bash
cd mohawk-sdk
pip install .
```

### Development Mode

```bash
pip install -e .
```

---

## Basic Usage

### 1. Import and Create Client

```python
from mohawk_sdk import MohawkClient, create_tensor

# Create client pointing to secure worker
client = MohawkClient(host="localhost", port=8003)
```

### 2. Load Model

```python
# Load ONNX model
with client.load_model("model.onnx") as session:
    print(f"Session loaded: {session}")
    
    # Get slice information
    slices = session.get_slice_info()
    for slice in slices:
        print(f"  - {slice['id']}: {slice['range']} on {slice['device']}")
```

### 3. Run Inference

```python
# Create input tensor
input_tensor = create_tensor((1, 4096), dtype="float32")

# Run inference
output = client.infer(session, input_tensor)

print(f"Output shape: {output.shape}")
```

### 4. Get Metrics

```python
# Get metrics for current session
metrics = client.get_metrics()
print(f"P50 latency: {metrics.get('p50_ms', 'N/A')}ms")
print(f"P95 latency: {metrics.get('p95_ms', 'N/A')}ms")
```

---

## Advanced Features

### Context Manager Pattern

The SDK uses Python's context manager protocol for automatic cleanup:

```python
from mohawk_sdk import MohawkClient, create_tensor

# Single-line inference with auto-cleanup
with MohawkClient(host="localhost", port=8003) as client:
    with client.load_model("model.onnx") as session:
        output = client.infer(session, create_tensor((1, 4096)))
        print(f"Result: {output}")

# Client automatically closes when exiting 'with' block
```

### Custom Device Mapping

Deploy model across multiple devices:

```python
from mohawk_sdk import MohawkClient

client = MohawkClient(host="localhost", port=8003)

with client.load_model(
    "model.onnx",
    device_map={
        "layer_0-1": "cuda:0",  # First two layers on GPU
        "layer_2-3": "cpu",      # Last two layers on CPU
    },
    slice_count=4
) as session:
    output = client.infer(session, input_tensor)
```

### Configuration Management

Create `~/.mohawk/config.toml`:

```toml
[worker]
host = "localhost"
port = 8003

[security]
pqc_enabled = true
replay_protection = true

[session]
max_concurrent_sessions = 100

[telemetry]
enabled = true
metrics_endpoint = "http://localhost:9090"
```

Load and modify configuration:

```python
from mohawk_sdk import MohawkConfig

config = MohawkConfig()

# Enable PQC encryption
config.set_pqc_enabled(True)

# Set max concurrent sessions
config.set_max_concurrent_sessions(100)

# Save to file
config.save()
```

---

## Benchmarking

### Run Performance Benchmarks

```python
from mohawk_sdk import MohawkClient, create_tensor, benchmark_inference

client = MohawkClient(host="localhost", port=8003)

with client.load_model("model.onnx") as session:
    input_tensor = create_tensor((1, 4096))
    
    # Run benchmark with warmup and iterations
    results = benchmark_inference(
        client=client,
        session=session,
        input_tensor=input_tensor,
        iterations=100,
        warmup=10
    )
    
    print("Benchmark Results:")
    print(f"  P50 Latency: {results['p50_ms']:.2f}ms")
    print(f"  P95 Latency: {results['p95_ms']:.2f}ms")
    print(f"  P99 Latency: {results['p99_ms']:.2f}ms")
    print(f"  Avg Latency: {results['avg_ms']:.2f}ms")
    print(f"  Throughput: {results['throughput_tokens_per_sec']:.1f} tokens/sec")
```

---

## Tensor Utilities

### Create Tensors

```python
from mohawk_sdk import create_tensor, create_random_tensor, create_batched_tensor

# Create zero tensor
tensor = create_tensor((8, 4096), dtype="float32")

# Create random tensor with seed for reproducibility
random_tensor = create_random_tensor(
    shape=(1, 4096),
    dtype="float32",
    rng_seed=42
)

# Create batched tensor (e.g., for text generation)
batched = create_batched_tensor(
    batch_size=8,
    seq_len=1,
    hidden_dim=4096,
    dtype="float32"
)

print(f"Batched tensor shape: {batched.shape}")
```

### Convert Tensor Dtypes

```python
from mohawk_sdk import convert_tensor_dtype

# Convert to float16 for memory efficiency
float16_tensor = convert_tensor_dtype(tensor, "float16")

print(f"Original dtype: {tensor.dtype}")
print(f"Converted dtype: {float16_tensor.dtype}")
```

---

## Monitoring and Metrics

### Metric Collector

Collect metrics from multiple inference runs:

```python
from mohawk_sdk import MetricCollector

collector = MetricCollector(max_history=1000)

# Record metrics after each inference
for i in range(10):
    output = client.infer(session, input_tensor)
    
    # Record snapshot
    collector.record(
        latency_p50_ms=12.5,
        latency_p95_ms=45.3,
        latency_p99_ms=78.2,
        throughput=80.2,
        active_sessions=1
    )

# Get percentiles
percentiles = collector.get_percentiles()
print(f"P50: {percentiles['p50_ms']:.2f}ms")
print(f"P95: {percentiles['p95_ms']:.2f}ms")
print(f"P99: {percentiles['p99_ms']:.2f}ms")
```

---

## Error Handling

### Handle Missing Models

```python
from mohawk_sdk import MohawkClient

client = MohawkClient(host="localhost", port=8003)

try:
    with client.load_model("nonexistent.onnx") as session:
        pass
except FileNotFoundError as e:
    print(f"Model not found: {e}")
```

### Handle Inference Errors

```python
from mohawk_sdk import MohawkClient

client = MohawkClient(host="localhost", port=8003)

try:
    with client.load_model("model.onnx") as session:
        output = client.infer(session, input_tensor)
except Exception as e:
    print(f"Inference failed: {e}")
    # Implement retry logic or fallback here
```

---

## Best Practices

### 1. Use Context Managers

Always use context managers for automatic cleanup:

```python
# ❌ Bad - manual cleanup required
client = MohawkClient(host="localhost", port=8003)
session = client.load_model("model.onnx")
output = client.infer(session, input_tensor)
# Forgot to close!

# ✅ Good - automatic cleanup
with MohawkClient(host="localhost", port=8003) as client:
    with client.load_model("model.onnx") as session:
        output = client.infer(session, input_tensor)
    # Automatically closed here
```

### 2. Enable PQC Encryption

Always enable PQC for production:

```python
client = MohawkClient(host="localhost", port=8003, secure=True)
```

### 3. Set Appropriate Timeouts

```python
client = MohawkClient(host="localhost", port=8003, timeout=30.0)
```

### 4. Monitor Metrics

Track performance over time:

```python
collector = MetricCollector()

with client.load_model("model.onnx") as session:
    for _ in range(100):
        output = client.infer(session, input_tensor)
        collector.record(...)
```

---

## Troubleshooting

### Connection Refused

**Error:** `Connection refused`  
**Solution:** Ensure worker is running:

```bash
python prototype/worker_secure.py --port 8003
```

### Model Not Found

**Error:** `FileNotFoundError`  
**Solution:** Verify model path exists and is accessible

### Timeout Errors

**Error:** `requests.exceptions.Timeout`  
**Solution:** Increase timeout or check worker health:

```python
client = MohawkClient(host="localhost", port=8003, timeout=60.0)
```

---

## Next Steps

- [ ] Read full [API documentation](../docs/SDK_GUI_PLAN.md)
- [ ] Explore [examples](../docs/examples.md)
- [ ] Run [benchmarks](../docs/benchmarks.md)
- [ ] Check out the [GUI application](../docs/GUI_PLANNING.md)

---

**Need Help?**  
Email: mohawk@sovereign-mohawk-proto.io  
GitHub Issues: https://github.com/rwilliamspbg-ops/Mohawk-Inference-Engine/issues
