# Mohawk Inference Engine

A high-performance, lightweight, and secure local inference and management engine for running LLM models. Designed to be significantly faster and leaner than standard LM Studio setups.

## Features

- **High Performance**: Optimized inference pipeline with minimal overhead
- **Lightweight**: Minimal dependencies and memory footprint
- **Secure**: Sandboxed execution and secure model loading
- **Model Management**: Easy model download, switching, and configuration
- **API Server**: RESTful API for model inference
- **Streaming Support**: Real-time token streaming responses
- **🆕 Professional GUI**: Beautiful, modern web interface with Gradio

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
python -m mohawk.server --port 8080

# Run inference
curl -X POST http://localhost:8080/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "max_tokens": 100}'

# Launch the GUI (NEW!)
python -m mohawk.gui.app
# Or use the CLI command:
mohawk-gui
```

## GUI Features

The new professional web interface includes:

- 💬 **Chat Interface**: Multi-turn conversations with markdown support
- 📁 **Model Manager**: Load models from HuggingFace or local paths
- ⚙️ **Parameter Controls**: Fine-tune generation with presets and custom settings
- 📊 **Metrics Dashboard**: Real-time performance monitoring
- 🎨 **Modern Design**: Dark/light themes, smooth animations, responsive layout

## Architecture

- `mohawk/` - Core engine module
  - `engine.py` - Main inference engine
  - `models/` - Model loading and management
  - `api/` - REST API endpoints
  - `gui/` - **NEW** Web interface components
  - `utils/` - Utility functions
- `tests/` - Test suite
- `benchmarks/` - Performance benchmarks

## Installation Options

```bash
# Basic installation
pip install -e .

# With GUI support
pip install -e ".[gui]"

# With GPU support
pip install -e ".[gpu]"

# For development
pip install -e ".[dev]"
```

## License

MIT
