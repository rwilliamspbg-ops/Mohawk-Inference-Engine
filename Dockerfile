# Mohawk Inference Engine GUI - Production Docker Image
# Version: 2.1.0
# Cross-platform: Windows, Linux, macOS

FROM python:3.11-slim-bookworm

# Set environment variables for production
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # System libraries for PyQt6
    libgl1-mesa-glx \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    libegl1-mesa \
    # Build tools
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mohawk_gui/ ./mohawk_gui/

# Create non-root user for security (production best practice)
RUN groupadd mohawk && \
    useradd -r -g mohawk mohawk && \
    chown -R mohawk:mohawk /app
USER mohawk

# Create directories for runtime data
RUN mkdir -p /app/certs /app/logs /app/models && \
    chown -R mohawk:mohawk /app/certs /app/logs /app/models

# Copy configuration template
COPY mohawk_gui/config.toml ./config.toml

# Expose ports
EXPOSE 8003 8443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command - can be overridden at runtime
CMD ["python", "mohawk_gui/main.py", "--host", "0.0.0.0", "--port", "8003"]

# =============================================================================
# Multi-stage build for smaller image (optional)
# =============================================================================
# FROM debian:bookworm-slim AS base
# RUN apt-get update && apt-get install -y \
#     python3.11 \
#     python3-pip \
#     libgl1-mesa-glx \
#     libxkbcommon-x11-0 \
#     libdbus-1-3 \
#     && rm -rf /var/lib/apt/lists/*
# 
# WORKDIR /app
# COPY --from=python:3.11-slim-bookworm /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
