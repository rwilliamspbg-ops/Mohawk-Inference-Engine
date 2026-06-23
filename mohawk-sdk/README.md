# Mohawk Inference Engine SDK v3.0

A user-friendly Python SDK for managing multi-device inference with Mohawk Inference Engine.

## Features

- **High-Level API**: Simple, intuitive interface for model deployment and inference
- **Session Management**: Context manager support for automatic cleanup
- **Distributed Inference**: Automatic partitioning across multiple workers
- **Metrics Collection**: Built-in telemetry for latency and throughput monitoring
- **Configuration Management**: Easy setup with TOML config files
- **Type-Safe**: Full type hints for better IDE support

## Installation

```bash
pip install mohawk-sdk
```

Or from source:

```bash
cd mohawk-sdk
pip install .
```

## Quick Start

### Basic Usage

```python
from mohawk_sdk import MohawkClient, create_tensor

# Create client
client = MohawkClient(host="localhost", port=8003)

# Load model and run inference
with client.load_model("model.onnx") as session:
    input_tensor = create_tensor((1, 4096))
    output = client.infer(session, input_tensor)
    print(f"Output shape: {output.shape}")

# Close client automatically on exit
client.close()
```

### Context Manager Pattern

The SDK uses Python's context manager protocol for automatic resource cleanup:

```python
from mohawk_sdk import MohawkClient

with MohawkClient(host="localhost", port=8003) as client:
    with client.load_model("model.onnx") as session:
        output = client.infer(session, input_tensor)
        # Resource cleanup happens automatically here
```

### Advanced Configuration

```python
from mohawk_sdk import MohawkClient, MohawkConfig

# Load configuration
config = MohawkConfig()
config.set_pqc_enabled(True)
config.set_max_concurrent_sessions(100)
config.save()

# Use configured client
client = MohawkClient(host="localhost", port=8003)
```

## API Reference

### MohawkClient

Main client class for inference operations.

```python
from mohawk_sdk import MohawkClient

client = MohawkClient(
    host="localhost",      # Worker host
    port=8003,             # Worker port
    secure=True,           # Enable PQC encryption (default)
    timeout=30.0,          # Request timeout in seconds
)

# Load model
session = client.load_model(
    model_path="model.onnx",
    device_map=None,       # Optional: {"layer_0-1": "cuda", ...}
    slice_count=2,         # Number of slices for partitioning
    preload=True           # Preload slices to workers
)

# Run inference
output = client.infer(session, input_tensor, options={})

# Get metrics
metrics = client.get_metrics()

# Close client
client.close()
```

### Session

Represents an active inference session.

```python
session = client.load_model("model.onnx")

# Get slice information
slices = session.get_slice_info()

# Set custom device mapping
session.set_device_map({
    "layer_0-1": "cuda",
    "layer_2-3": "cpu"
})

# Get metrics
metrics = session.get_metrics()

# Reset session
session.reset()
```

### MohawkConfig

Configuration manager.

```python
from mohawk_sdk import MohawkConfig

config = MohawkConfig()

# Enable PQC encryption
config.set_pqc_enabled(True)

# Set max concurrent sessions
config.set_max_concurrent_sessions(100)

# Get worker URL
url = config.get_worker_url()

# Discover workers
workers = config.discover_workers()

# Register worker
config.register_worker({"id": "worker-1", "status": "online"})
```

### MetricCollector

Collect and aggregate metrics.

```python
from mohawk_sdk import MetricCollector

collector = MetricCollector(max_history=1000)

# Record metrics
snapshot = collector.record(
    latency_p50_ms=12.5,
    latency_p95_ms=45.3,
    latency_p99_ms=78.2,
    throughput=80.2,
    active_sessions=5
)

# Get percentiles
percentiles = collector.get_percentiles()

# Get history
history = collector.get_history(limit=100)
```

### Utility Functions

#### create_tensor

Create tensor with specified shape and dtype.

```python
from mohawk_sdk import create_tensor, create_random_tensor

# Create zero tensor
tensor = create_tensor((8, 4096), dtype="float32")

# Create random tensor
random_tensor = create_random_tensor((1, 4096), dtype="float32", rng_seed=42)

# Create batched tensor
batched = create_batched_tensor(batch_size=8, seq_len=1, hidden_dim=4096)
```

#### load_model_from_file

Load model from file (ONNX or TorchScript).

```python
from mohawk_sdk import load_model_from_file

model = load_model_from_file("model.onnx")
```

#### benchmark_inference

Benchmark inference performance.

```python
from mohawk_sdk import benchmark_inference

results = benchmark_inference(
    client=client,
    session=session,
    input_tensor=input_tensor,
    iterations=100,
    warmup=10
)

print(results)
# {
#     "p50_ms": 12.5,
#     "p95_ms": 45.3,
#     "p99_ms": 78.2,
#     "avg_ms": 15.8,
#     "throughput_tokens_per_sec": 63.2
# }
```

## Examples

### Text Generation

```python
from mohawk_sdk import MohawkClient, create_batched_tensor

client = MohawkClient(host="localhost", port=8003)

with client.load_model("llama-7b.onnx") as session:
    # Create input prompt
    input_ids = create_tensor((1, 1), dtype="int32")
    
    # Generate tokens
    for i in range(100):
        output = client.infer(session, input_ids)
        input_ids = output[:1]  # Take first token as new input
    
    print("Generated text:")
    # ... decode and print
```

### Multi-Device Deployment

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

### Monitoring and Metrics

```python
from mohawk_sdk import MohawkClient, MetricCollector

client = MohawkClient(host="localhost", port=8003)

# Create metrics collector
collector = MetricCollector()

with client.load_model("model.onnx") as session:
    for _ in range(10):
        output = client.infer(session, input_tensor)
        
        # Record metrics
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
```

## Configuration File

Create `~/.mohawk/config.toml`:

```toml
[worker]
host = "localhost"
port = 8003

[security]
pqc_enabled = true
replay_protection = true
nonce_expiry_seconds = 3600

[session]
max_concurrent_sessions = 100
circuit_breaker_threshold = 5
circuit_breaker_timeout = 30

[telemetry]
enabled = true
metrics_endpoint = "http://localhost:9090"
```

## Development

### Building from Source

```bash
cd mohawk-sdk
pip install .
```

### Running Tests

```bash
pytest tests/ -v
```

### Developing

```bash
# Install in editable mode
pip install -e .

# Run with debugger
python -m pdb your_script.py
```

## Documentation

- [SDK API Reference](docs/api.md)
- [Examples Guide](docs/examples.md)
- [Performance Benchmarks](docs/benchmarks.md)
- [Troubleshooting](docs/troubleshooting.md)

## Support

- **Repository:** https://github.com/rwilliamspbg-ops/Mohawk-Inference-Engine
- **Issues:** Create GitHub issue
- **Email:** mohawk@sovereign-mohawk-proto.io

## License

Apache-2.0. See [LICENSE](../LICENSE).

---

**Mohawk Inference Engine SDK v3.0**  
*Maintained by: Mohawk Ops Team, Sovereign Mohawk Proto LLC*
