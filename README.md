# Mohawk Inference Engine

<div align="center">

![Mohawk Logo](https://img.shields.io/badge/Mohawk-LLM_Inference-orange)
![License](https://img.shields.io/badge/license-MIT-blue)
![Rust](https://img.shields.io/badge/rust-1.75+-orange)
![Docker](https://img.shields.io/badge/docker-ready-blue)

**Production-ready LLM inference engine with GGUF support and OpenAI-compatible API**

[Features](#features) • [Quick Start](#quick-start) • [Documentation](#documentation) • [Benchmarks](#benchmarks) • [API Reference](#api-reference)

</div>

---

## 🚀 Features

### Core Capabilities
- **🦙 llama.cpp Integration**: Native GGUF model support with quantization (Q4_K_M, Q5_K_M, Q8_0, etc.)
- **⚡ High Performance**: Optimized token generation with PagedAttention-inspired memory management
- **🌊 Streaming Support**: Real-time token streaming via Server-Sent Events (SSE)
- **🔌 OpenAI Compatible**: Drop-in replacement for OpenAI API endpoints
- **📥 Auto-Download**: Automatic model downloading from HuggingFace Hub
- **💻 Hardware Acceleration**: CPU and CUDA GPU support with automatic detection

### Enterprise Features
- **📊 Live Metrics**: Prometheus-compatible metrics endpoint
- **🔐 Authentication**: JWT and API key authentication
- **📈 Rate Limiting**: Configurable request rate limiting per user/API key
- **🎛️ Model Management**: Load/unload models dynamically without restart
- **🔄 Multi-Model**: Run multiple models simultaneously with memory isolation
- **📝 Structured Logging**: JSON logging with tracing integration

### Developer Experience
- **🎨 Modern GUI**: React-based web interface (LM Studio style)
- **📖 MCP Protocol**: Full Model Context Protocol support
- **🧪 Testing**: Comprehensive test suite with integration tests
- **🐳 Docker Ready**: Pre-built images for CPU and CUDA deployments
- **🔄 CI/CD**: GitHub Actions pipeline for automated testing and deployment

---

## 🏁 Quick Start

### Using Docker (Recommended)

**CPU Version:**
```bash
docker run -d -p 8080:8080 \
  -v ./models:/app/models \
  ghcr.io/mohawk-inference/mohawk-server:latest
```

**CUDA Version (GPU):**
```bash
docker run -d --gpus all -p 8080:8080 \
  -v ./models:/app/models \
  ghcr.io/mohawk-inference/mohawk-server-cuda:latest
```

### From Source

```bash
# Clone repository
git clone https://github.com/mohawk-inference/mohawk.git
cd mohawk/mohawk-server

# Install dependencies (Ubuntu/Debian)
sudo apt-get install cmake clang libssl-dev pkg-config

# Build
cargo build --release

# Run
./target/release/mohawk-server
```

### Download a Model

```bash
# Using the API
curl -X POST http://localhost:8080/api/models/download \
  -H "Content-Type: application/json" \
  -d '{
    "repo_id": "TheBloke/Llama-2-7B-Chat-GGUF",
    "filename": "llama-2-7b-chat.Q4_K_M.gguf"
  }'

# Load the model
curl -X POST http://localhost:8080/api/models/llama-2-7b/load
```

---

## 📖 Documentation

### Configuration

Create `mcp.json` in the server directory:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8080,
    "model_path": "./models"
  },
  "models": [
    {
      "id": "llama-2-7b",
      "name": "Llama 2 7B Chat",
      "path": "TheBloke/Llama-2-7B-Chat-GGUF/llama-2-7b-chat.Q4_K_M.gguf",
      "source": "huggingface",
      "parameters": 7000000000,
      "quantization": "Q4_K_M",
      "size_gb": 4.2
    }
  ],
  "system_prompts": {
    "default": "You are a helpful AI assistant.",
    "coding": "You are an expert programmer. Write clean, efficient code.",
    "creative": "You are a creative writer. Be imaginative and engaging."
  },
  "metrics": {
    "enabled": true,
    "endpoint": "/metrics"
  }
}
```

### API Endpoints

#### Chat Completions (OpenAI Compatible)

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-2-7b",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "temperature": 0.7,
    "max_tokens": 512,
    "stream": false
  }'
```

#### Streaming Response

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-2-7b",
    "messages": [{"role": "user", "content": "Tell me a story"}],
    "stream": true
  }'
```

#### Model Management

```bash
# List models
curl http://localhost:8080/api/models

# Load model
curl -X POST http://localhost:8080/api/models/{model_id}/load

# Unload model
curl -X POST http://localhost:8080/api/models/{model_id}/unload

# Get model status
curl http://localhost:8080/api/models/{model_id}/status
```

#### Health & Metrics

```bash
# Health check
curl http://localhost:8080/health

# Prometheus metrics
curl http://localhost:8080/metrics
```

---

## 📊 Benchmarks

| Model | Quantization | Hardware | Tokens/sec | VRAM |
|-------|-------------|----------|------------|------|
| Llama 2 7B | Q4_K_M | RTX 4090 | 95 t/s | 5.2 GB |
| Llama 2 7B | Q4_K_M | M2 Max | 42 t/s | 5.2 GB |
| Llama 2 7B | Q4_K_M | Ryzen 9 7950X | 18 t/s | 5.2 GB |
| Mistral 7B | Q5_K_M | RTX 4090 | 88 t/s | 6.1 GB |
| Phi-3 Mini | Q8_0 | RTX 4090 | 145 t/s | 4.8 GB |

*Higher is better for tokens/sec*

---

## 🎨 GUI Features

The included web interface provides:

- **Model Selector**: Switch between loaded models instantly
- **Chat Sessions**: Create, manage, and delete conversations
- **Settings Panel**: Adjust temperature, top_p, top_k, max tokens
- **System Prompts**: Choose from predefined or custom system prompts
- **Live Metrics**: View tokens/sec, memory usage, and latency
- **Dark Theme**: Easy on the eyes for extended sessions

### Running the GUI

```bash
cd gui
npm install
npm run dev
```

Open http://localhost:3000 in your browser.

---

## 🔧 Advanced Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_PATH` | `./models` | Directory for model storage |
| `RUST_LOG` | `info` | Log level (trace, debug, info, warn, error) |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8080` | Server port |
| `API_KEY` | `none` | Optional API key for authentication |
| `MAX_REQUESTS_PER_MINUTE` | `60` | Rate limit per API key |

### Custom Prompt Templates

Mohawk supports custom chat templates:

```rust
// In mcp.json
{
  "prompt_template": {
    "system": "<|system|>\n{system}\n</s>",
    "user": "<|user|>\n{message}\n</s>",
    "assistant": "<|assistant|>\n{message}\n</s>"
  }
}
```

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone and setup
git clone https://github.com/mohawk-inference/mohawk.git
cd mohawk

# Server development
cd mohawk-server
cargo watch -x run

# GUI development
cd gui
npm run dev
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [llama.cpp](https://github.com/ggerganov/llama.cpp) for the incredible GGUF inference backend
- [HuggingFace](https://huggingface.co) for the model hub
- [OpenAI](https://openai.com) for the API standard
- The entire open-source AI community

---

<div align="center">

**Built with ❤️ using Rust & React**

[Report Bug](https://github.com/mohawk-inference/mohawk/issues) • [Request Feature](https://github.com/mohawk-inference/mohawk/issues)

</div>
