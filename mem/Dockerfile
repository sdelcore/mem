# Dockerfile for Mem backend
# Transcription handled by external STTD service

FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

COPY pyproject.toml .
COPY README.md .

RUN uv venv && \
    uv pip install --upgrade pip && \
    uv pip install -e .

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 memuser && \
    mkdir -p /app /data/db /data/uploads /data/config && \
    chown -R memuser:memuser /app /data

WORKDIR /app

COPY --from=builder --chown=memuser:memuser /app/.venv /app/.venv

COPY --chown=memuser:memuser src/ ./src/
COPY --chown=memuser:memuser config.yaml ./config.yaml

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"

USER memuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/status || exit 1

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
