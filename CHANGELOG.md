# 🦅 Mohawk Inference Engine - Changelog

All notable changes to the project will be documented in this file.

## [2.1.1] - 2026-07-11

### 🔧 Devcontainer and Setup Reliability

- Updated `.devcontainer/devcontainer.json`:
	- workspace path compatibility for Codespaces
	- docker-outside-of-docker feature enablement
	- Python and Docker VS Code extension recommendations
	- explicit bash post-create invocation
- Updated `.devcontainer/Dockerfile` with missing runtime and diagnostics packages.
- Reworked `.devcontainer/post_create.sh` to be idempotent, root-safe, and configurable with:
	- `MOHAWK_SKIP_LIBOQS_BUILD=1`
	- `MOHAWK_SKIP_PY_DEPS=1`

### 🖥️ Full-Stack Desktop GUI Launch Improvements

- Fixed startup ordering in `mohawk_gui/main_window.py`:
	- initialize status bar before tab refresh paths
	- start background health thread only after UI widget initialization
- Added environment-based backend URL overrides for desktop GUI runtime.
- Added reusable desktop GUI launcher flow in `launch.py` for both native and Docker orchestration.
- Updated `launch.sh` dependency probe to include `PyQt6`.
- Added `mohawk-desktop-gui` service to `docker-compose.yml`.
- Added full-stack parity services to `docker-compose.dev.yml` and adjusted conflicting host port mapping.

### 📚 Documentation Updates

- Updated `README.md` quick-start and documentation index.
- Updated `QUICKSTART.md` with launcher/devcontainer paths and focused model/chat smoke checks.
- Updated `DOCKER_SETUP.md` desktop GUI behavior notes and skip flag usage.
- Added `INSTALL.md` and `SETUP.md` for clear install/runtime guidance.

### ✅ Validation

- End-to-end functional test executed: `python test_user_functions.py`.
- Result: `33/33 passed (100.0%)` including model list/load and chat inference paths.

## [2.1.0] - 2024-01-15

### 🎉 Major Release: Professional Dashboard with LM Studio Features

#### ✨ New Features

**Dashboard UI Complete**
- ✅ Implemented comprehensive tab-based interface with 7 main sections
- ✅ Model Library Manager (LM Studio-style) with download/upload capabilities
- ✅ Real-time Chat Interface with context management
- ✅ Performance Metrics Dashboard with PyQtGraph charts
- ✅ Session Manager with priority queue system
- ✅ Worker Configuration with multi-device layer splitting
- ✅ Security Center with PQC + mTLS + JWT authentication
- ✅ Conversation History with usage analytics

#### 📚 Model Library Features

**Model Management**
- Browse available models with search and filters
- Download models from Hugging Face or other sources
- Upload local model files (.safetensors, .bin)
- Quantization options: Q4_K_M, Q5_K_M, Q8_0, FP16
- Device splitting configuration for multi-device inference
- Model status tracking (Ready/Loading/Failed)

**Model Details Panel**
- Load selected model with one click
- Configure device split format: `cpu_threads;gpu_ids`
- Real-time load progress indicator
- Error recovery options on failure

#### 💬 Chat Interface Features

**Conversation Management**
- Multi-turn conversations with full context retention
- Scrollable conversation history (500+ lines)
- System prompt customization
- Context size monitoring and management

**Generation Controls**
- Temperature slider (0.0 - 2.0, default: 0.7)
- Top-p sampling parameter (default: 0.9)
- Max tokens setting (1 - 8192, default: 2048)
- Send message with Enter key or Send button

**Input Features**
- Placeholder text for guidance
- Shift+Enter for new line
- Auto-scroll to bottom on new messages
- Clear history button for cleanup

#### 📊 Performance Metrics Features

**Real-time Charts (PyQtGraph)**
- Throughput chart: Requests per second
- Latency percentiles: p50, p95, p99
- Resource usage charts: CPU, Memory, GPU
- Peak throughput tracking

**Statistics Summary**
- Total requests processed
- Average latency across sessions
- Success rate percentage
- Active sessions count
- Peak throughput recorded

#### 🔗 Session Manager Features

**Session Table**
- Session ID with auto-generation
- Model name display
- Status indicators (Queued/Running/Completed)
- Throughput metrics per session
- Latency percentiles
- Tokens per second
- Start time timestamp
- Cancel action per session

**Queue Configuration**
- Max queue size spinner (1 - 1000, default: 50)
- Priority queue buttons (High/Normal)
- Visual status indicators by priority
- Session lifecycle management

#### ⚙️ Worker Configuration Features

**Worker Management Table**
- Worker ID auto-generation
- Host:Port configuration
- Connection status (Connected/Disconnected)
- Model name per worker
- GPU thread count spinner
- Load progress indicator
- Connect/Disconnect actions
- Restart failed workers

**Multi-device Support**
- Device splitting configuration panel
- Layer distribution across workers
- GPU thread allocation per device
- Load balancing monitoring

#### 🔒 Security Center Features

**JWT Authentication**
- Status indicator (Enabled/Disabled)
- Algorithm display (RS256)
- Token expiry time (24 hours default)
- Refresh token button
- Validation status

**mTLS Configuration**
- Certificate validity check
- Client certificate path
- Key encryption status (Fernet)
- Certificate renewal reminders

**Post-Quantum Cryptography (PQC)**
- Hybrid KEM support toggle
- X25519 + Kyber integration
- liboqs status display
- Enable/disable with confirmation
- Quantum-resistant security layer

**Security Event Log**
- Immutable audit trail
- Timestamped events
- Action type categorization
- Resource tracking

#### 📜 Conversation History Features

**History Table**
- Timestamp for each conversation
- Model used identifier
- Tokens consumed count
- Duration of conversation
- Status (Completed/Failed)
- Actions (view, delete, export)

**Usage Statistics**
- Total tokens processed
- Average latency across all sessions
- Models usage count
- Recent activity summary

#### 🎨 UI/UX Improvements

**Navigation**
- Tab-based interface for organized access
- Navigation toolbar with icon buttons
- Quick tab switching
- Status bar with real-time updates

**Visual Design**
- Professional color scheme (green success, orange warnings)
- Emoji icons for quick identification
- Bold status indicators
- Consistent button styling
- Rounded corners for modern look

**Shortcuts**
- Ctrl+Shift+M: Show/Hide main window (tray icon)
- Shift+Enter: New line in chat
- Enter: Send message
- F1: Show help

#### 🔧 Technical Improvements

**Architecture**
- Modular page design for maintainability
- Event-driven architecture with signals/slots
- Thread-safe metrics updates
- Memory-efficient data structures

**Dependencies**
- PyQt6 >= 6.5.0 (production-ready)
- PyQtGraph >= 0.13.0 (fast charts)
- cryptography >= 41.0.0 (security)
- PyJWT >= 2.8.0 (token handling)
- psutil >= 5.9.0 (system monitoring)

**Code Quality**
- Comprehensive docstrings
- Type hints for all functions
- Error handling with graceful degradation
- Input validation and sanitization

#### 📚 Documentation Added

- **DASHBOARD_FEATURES.md** - Complete feature documentation
- **QUICK_START.md** - 3-minute setup guide
- **GUI_DASHBOARD_SUMMARY.md** - Executive summary
- Updated README.md with dashboard showcase
- Inline code comments for all components

---

## [2.0.0] - Previous Version

### Core Features (Production Ready)
- JWT Authentication with RSA signatures
- mTLS Support for secure communication
- Connection Pooling for high concurrency
- Metrics Buffering with configurable windows
- Graceful Error Handling with recovery strategies
- Session Persistence and Checkpointing
- Performance Monitoring (Memory, CPU, GPU)
- Audit Logging for compliance

---

## [1.0.0] - Initial Release

### Prototype Features
- Basic controller and worker architecture
- Secure communication with X25519
- Session management foundation
- Telemetry hooks for monitoring

---

## 📋 Migration Guide from 2.0.0 to 2.1.0

### Breaking Changes: None

The upgrade is seamless - all existing functionality is preserved while adding new dashboard features.

### New Configuration Options

```toml
# Add to config.toml if needed
[dashboard]
enable_metrics_charts = true
metrics_update_interval_ms = 1000
max_history_items = 100
```

### Migration Steps

1. **No code changes required** - Dashboard is backward compatible
2. **Dependencies auto-resolve** - PyQt6 and PyQtGraph will be installed if missing
3. **Existing models remain accessible** - Model library loads all available models
4. **Worker connections preserved** - Existing workers automatically connect

---

## 🎯 Roadmap for Future Versions

### Version 2.2.0 (Planned)
- [ ] Advanced chat history export (JSON, PDF)
- [ ] Model comparison tools
- [ ] Prompt template library
- [ ] Batch inference support
- [ ] Advanced analytics dashboard

### Version 2.3.0 (Planned)
- [ ] Plugin system for custom models
- [ ] API endpoint management
- [ ] Multi-user collaboration features
- [ ] Real-time collaboration in chat

### Version 2.4.0 (Planned)
- [ ] Mobile companion app integration
- [ ] Voice-to-text input
- [ ] Advanced prompt engineering tools
- [ ] Model distillation utilities

---

## 🙏 Acknowledgments

### Inspiration
- **LM Studio** - For user-friendly model interface design
- **Ollama** - For model management concepts
- **vLLM** - For performance optimization techniques

### Contributors
Thank you to all contributors who helped build Mohawk Inference Engine!

---

## 📞 Support

For issues, questions, or contributions:
- GitHub Issues: [Open an issue](https://github.com/your-org/mohawk-inference-engine/issues)
- Documentation: See `/docs` directory
- Quick Start: `mohawk_gui/QUICK_START.md`

---

**Mohawk Inference Engine v2.1.0 - Professional Dashboard Released!** 🦅
