# Multi-stage Dockerfile for Mem backend with Faster-Whisper GPU support
# Optimized for GTX 1080 Ti with CUDA support
# Uses CUDA 12.6 with cuDNN 9 for compatibility with ctranslate2 4.x / faster-whisper 1.x

# Stage 1: Builder
FROM nvidia/cuda:12.6.3-cudnn-devel-ubuntu22.04 AS builder

# Prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# Install system dependencies and Python 3.10 (Ubuntu 22.04 default)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    ffmpeg \
    git \
    curl \
    wget \
    pkg-config \
    libcairo2-dev \
    libgirepository1.0-dev \
    gir1.2-glib-2.0 \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3 /usr/bin/python

# Install uv for fast Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy dependency files
COPY pyproject.toml .
COPY README.md .

# Install dependencies with uv
RUN uv venv && \
    uv pip install --upgrade pip && \
    uv pip install -e .

# Pre-download Faster-Whisper model during build to avoid runtime downloads
# This caches the model in the image
RUN .venv/bin/python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"

# Stage 2: Runtime
FROM nvidia/cuda:12.6.3-cudnn-runtime-ubuntu22.04

# Environment setup
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV CUDA_VISIBLE_DEVICES=0

# Install runtime dependencies (including PyGObject/sttd requirements)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    ffmpeg \
    libgomp1 \
    libcairo2 \
    libgirepository-1.0-1 \
    gir1.2-glib-2.0 \
    libportaudio2 \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3 /usr/bin/python

# Create non-root user for security
RUN useradd -m -u 1000 memuser && \
    mkdir -p /app /data/db /data/uploads /data/config && \
    chown -R memuser:memuser /app /data

WORKDIR /app

# Copy Python environment from builder
COPY --from=builder --chown=memuser:memuser /app/.venv /app/.venv
COPY --from=builder --chown=memuser:memuser /root/.cache/huggingface /home/memuser/.cache/huggingface

# Copy application code
COPY --chown=memuser:memuser src/ ./src/
COPY --chown=memuser:memuser config.yaml ./config.yaml

# Set up Python path
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"

# Switch to non-root user
USER memuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/health')" || exit 1

# Expose API port
EXPOSE 8000

# Default command
CMD ["python", "-m", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]