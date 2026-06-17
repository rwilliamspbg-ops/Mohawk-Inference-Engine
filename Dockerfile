# Mohawk Inference Engine GUI - Production Docker Image
# Version: 2.1.0

FROM python:3.14-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     PIP_NO_CACHE_DIR=1     PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y     gcc     git     libgl1-mesa-glx     libglib2.0-0     libxkbcommon-x11-0     libdbus-1-3     && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mohawk_gui/ ./mohawk_gui/

# Create non-root user for security
RUN groupadd mohawk && useradd -r -g mohawk mohawk
USER mohawk

# Expose ports
EXPOSE 8003 8443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3     CMD python -c "import sys; sys.exit(0 if __import__('mohawk_gui').main else 1)" || exit 1

# Default command
CMD ["python", "mohawk_gui/main.py"]
