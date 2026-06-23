# IMPROVED PYPROJECT.TOML FOR MOHAWK INFERENCE ENGINE
# This file shows recommended changes to the current pyproject.toml

[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "mohawk-inference-engine"
version = "2.1.0"
description = "Production-ready distributed inference engine with multi-device model splitting and post-quantum cryptography"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.10"
authors = [
    {name = "Mohawk Inference Engine Team", email = "team@mohawk-inference.example.com"}
]
keywords = ["inference", "gpu", "ml", "distributed", "gui", "pqc"]
classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Topic :: System :: Networking",
]

# CORE DEPENDENCIES - Required for GUI
dependencies = [
    "PyQt6>=6.5.0",
    "cryptography>=41.0.0",
    "PyJWT>=2.8.0",
    "psutil>=5.9.0",
    "websockets>=11.0",
    "pyqtgraph>=0.13.0",
    "tomli>=2.0.1",
    "pydantic>=2.5.0",
    "httpx>=0.24.0",
    "aiohttp>=3.9.0",
    "loguru>=0.7.0",
]

[project.optional-dependencies]
# Prototype: Worker + Controller implementation
prototype = [
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
    "numpy>=1.24.0",
    "requests>=2.31.0",
]

# Post-Quantum Cryptography (optional, liboqs-python must be installed separately)
pqc = [
    # liboqs-python>=1.0.0  # Install separately: pip install liboqs-python
]

# Development: Testing, formatting, security
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-qt>=4.2.0",
    "pytest-cov>=4.1.0",  # Code coverage tracking
    "black>=23.12.0",
    "isort>=5.12.0",
    "flake8>=6.1.0",
    "mypy>=1.5.0",
    "bandit>=1.7.0",  # Security linter
    "safety>=2.3.0",  # Dependency vulnerability scanner
]

# Deployment: Building executables and Docker
deployment = [
    "PyInstaller>=6.0.0",
    "virtualenv>=20.24.0",
]

# All-in-one for local development
all = [
    "mohawk-inference-engine[prototype,dev,deployment]"
]

[project.scripts]
mohawk-gui = "mohawk_gui.main:main"
mohawk-worker = "prototype.worker_secure:main"
mohawk-controller = "prototype.controller_secure:main"

[tool.setuptools.packages.find]
include = ["mohawk_gui*", "prototype*"]

[tool.setuptools.package-data]
mohawk_gui = ["resources/**/*", "*.toml", "*.conf"]

# ============================================================================
# TESTING CONFIGURATION
# ============================================================================

[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "security: marks tests as security tests",
    "crypto: marks tests as cryptography tests",
    "gui: marks tests as GUI/Qt tests",
]
testpaths = ["prototype", "tests"]
python_files = ["test_*.py", "*_test.py"]
addopts = "-v --tb=short --strict-markers"
asyncio_mode = "auto"

# ============================================================================
# CODE QUALITY CONFIGURATION
# ============================================================================

[tool.black]
line-length = 88
target-version = ['py310', 'py311', 'py312']
include = '\.pyi?$'
exclude = '''
/(
    \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | _build
  | buck-out
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
line_length = 88
multi_line_mode = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # Gradually enable
disallow_incomplete_defs = false
ignore_missing_imports = true
plugins = []

# PyQt6 is not fully typed, so ignore its errors
[[tool.mypy.overrides]]
module = ["PyQt6.*"]
ignore_errors = true

[[tool.mypy.overrides]]
module = ["cryptography.*"]
ignore_errors = true

[tool.bandit]
exclude_dirs = ["tests", "docs"]
skips = ["B404", "B603"]  # subprocess, not a security risk here

[tool.coverage.run]
source = ["mohawk_gui", "prototype"]
omit = ["*/tests/*", "*/__main__.py", "*/main.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
precision = 2

# ============================================================================
# BUILD CONFIGURATION
# ============================================================================

[tool.setuptools.dynamic]
version = {attr = "mohawk_gui.__version__"}

# Recommended: Create mohawk_gui/__init__.py with:
# __version__ = "2.1.0"

# ============================================================================
# INSTALLATION EXAMPLES
# ============================================================================

# Install GUI only (default):
#   pip install mohawk-inference-engine
#
# Install with prototype/worker:
#   pip install mohawk-inference-engine[prototype]
#
# Install with everything (development):
#   pip install mohawk-inference-engine[all]
#
# Install with specific extras:
#   pip install mohawk-inference-engine[prototype,dev]
#
# For local development:
#   pip install -e .[all]

# ============================================================================
# MIGRATION GUIDE FROM CURRENT pyproject.toml
# ============================================================================

# CHANGES FROM CURRENT:
#
# 1. Added [project.optional-dependencies]
#    - prototype: fastapi, uvicorn, numpy (for worker/controller)
#    - pqc: placeholder for liboqs-python
#    - dev: added pytest-cov, isort, bandit, safety
#    - deployment: explicit build tools
#    - all: convenience group
#
# 2. Added [project.scripts]
#    - mohawk-worker and mohawk-controller entry points
#    - Allows `mohawk-worker` from command line
#
# 3. Added tool configurations
#    - [tool.black] - formatting settings
#    - [tool.isort] - import sorting
#    - [tool.mypy] - type checking (start non-strict)
#    - [tool.bandit] - security linting
#    - [tool.coverage] - test coverage tracking
#
# 4. Better comments and organization
#
# IMPLEMENTATION STEPS:
# 1. Back up current pyproject.toml
# 2. Update [project.optional-dependencies]
# 3. Add [project.scripts] entry points
# 4. Add tool configuration sections
# 5. Update CI/CD to use `pip install -e .[all]`
# 6. Update docs/CONTRIBUTING.md with new dependencies
# 7. Run: black . && isort . && pytest --cov

