# Mohawk Inference Engine GUI - Production Docker Image
# Version: 2.1.0 - Linux/ARM64 Optimized

FROM python:3.12-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies (Debian Bookworm compatible)
# Includes build tools for ARM64 and service discovery support
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    git \
    curl \
    pkg-config \
    libffi-dev \
    libssl-dev \
    libgl1 \
    libegl1 \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    avahi-daemon \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
# Use --no-build-isolation for compatibility with ARM64
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir \
        "fastapi>=0.104.0" \
        "uvicorn>=0.24.0" \
        "requests>=2.31.0"

# Copy application code
COPY mohawk_gui/ ./mohawk_gui/
COPY prototype/ ./prototype/

# Create non-root user for security
RUN groupadd mohawk && useradd -r -g mohawk mohawk && \
    chown -R mohawk:mohawk /app

# Expose ports
EXPOSE 8003 8443

# Health check with timeout and retries
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Default command - run GUI backend with service discovery
CMD ["python", "-m", "uvicorn", "prototype.gui_backend:app", "--host", "0.0.0.0", "--port", "8003"]
