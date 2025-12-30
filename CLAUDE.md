# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mem is a video processing and streaming system that captures frames and transcriptions from video files and live streams, storing them with absolute UTC timestamps in a DuckDB database. The architecture follows "capture first, process later" principle with ~95% storage reduction through perceptual hash deduplication.

Key features:
- Process video files (must be named `YYYY-MM-DD_HH-MM-SS.mp4`)
- Receive multiple concurrent RTMP streams from OBS Studio
- Extract frames with configurable intervals
- Generate transcriptions using Whisper
- Store frames as BLOBs with deduplication
- Timeline-based temporal queries

## Development Commands

### Backend (Python/FastAPI)
```bash
cd mem/
uv sync                                          # Install dependencies
uv add package-name                              # Add new dependency
uv run uvicorn src.api.app:app --reload --port 8000  # Start API server
uv run pytest tests/                            # Run all tests
uv run pytest tests/test_db.py -v              # Run specific test file
uv run pytest tests/test_api_services.py -v    # Test API services
uv run pytest tests/test_models.py -v          # Test Pydantic models
uv run pytest tests/test_frame.py -v           # Test frame processing
uv run pytest -k "test_name" -v                 # Run specific test by name
uv run pytest tests/ --cov=src --cov-report=html # Run with coverage report
make install                                     # Install dependencies with uv sync
make format                                      # Format code with black and ruff --fix
make lint                                        # Run ruff linter
make clean                                       # Clean all build artifacts and caches
```

### Frontend (React/TypeScript)
```bash
cd mem-ui/
npm install                                      # Install dependencies
npm run dev                                      # Start dev server (port 5173, proxies to backend on 8000)
npm run test                                     # Run tests with Vitest
npm run test:ui                                  # Run tests with UI
npm run build                                    # Build for production
npm run lint                                     # Run ESLint
npm run preview                                  # Preview production build
```

### Full Stack
```bash
./start-mem.sh                                   # Start backend (port 8000) and frontend (port 3000)
./stop-mem.sh                                    # Stop all services

# Monitor logs while running
tail -f /tmp/mem-backend.log                    # Backend logs
tail -f /tmp/mem-frontend.log                   # Frontend logs
```

### Docker Development
```bash
# GPU mode (requires NVIDIA GPU for STTD transcription)
docker compose --profile gpu up -d

# CPU mode (slower transcription, no GPU required)
docker compose --profile cpu up -d

# Build specific service
docker compose build mem-backend
docker compose build mem-frontend
docker compose build mem-rtmp

# View logs
docker compose logs -f mem-backend
docker compose logs -f mem-frontend
docker compose logs -f mem-sttd

# Stop all services
docker compose down

# Clean up volumes
docker compose down -v
```

### Nix Development Environment
```bash
# Enter Nix development shell with all dependencies
nix develop

# Run commands directly with Nix
nix develop -c uv run uvicorn src.api.app:app --reload
nix develop -c uv run pytest tests/

# Why use Nix develop?
# - Provides reproducible environment with exact versions
# - Includes system dependencies (Python 3.9, FFmpeg, DuckDB CLI)
# - Ensures consistent development across machines
```

## Architecture

### Core Design Principles
- **Temporal Architecture**: All data anchored to absolute UTC timestamps parsed from filenames
- **Storage Optimization**: Perceptual hashing achieves ~95% deduplication for static scenes
- **Strict Input Format**: Videos MUST be named `YYYY-MM-DD_HH-MM-SS.mp4` (UTC time)
- **Database Storage**: Frames stored as JPEG BLOBs in DuckDB, no filesystem dependencies
- **Stream Support**: RTMP streams from OBS Studio with auto-resolution detection
- **Decoupled Transcription**: STTD service handles speech-to-text with speaker diarization (GPU or CPU)
- **Capture First**: Raw data capture separated from analysis/processing

### Backend Structure (`mem/src/`)
```
api/
├── app.py           # FastAPI application setup
├── routes.py        # API endpoints
├── services.py      # Business logic layer
├── models.py        # Request/response schemas
├── settings.py      # Application settings
├── exceptions.py    # Custom exception classes
└── voice_profiles.py # Voice profile management

capture/
├── pipeline.py      # Main processing orchestrator
├── extractor.py     # Frame extraction, timestamp parsing
├── transcriber.py   # Transcription via STTD client
├── sttd_client.py   # HTTP client for STTD service
├── frame.py         # Perceptual hashing, deduplication
└── stream_server.py # Stream session management, nginx-rtmp callbacks

storage/
├── db.py            # DuckDB operations
├── models.py        # Pydantic data models
└── schema.sql       # Database schema definition
```

### Frontend Structure (`mem-ui/src/`)
```
components/
├── Timeline/        # Timeline navigation with TimelineSegment
├── Search/          # Search interface
├── Content/         # Frame and transcription viewer
├── Upload/          # Video upload interface
└── Stream/          # Live streaming components

hooks/
├── useTimeline.ts   # Timeline data fetching
├── useStreams.ts    # Stream management
└── useSearch.ts     # Search functionality

utils/
└── api.ts           # API client with axios
```

### Database Schema (DuckDB)
Key tables with temporal indexing:
- `sources`: Video/stream sources with UTC timestamps
- `unique_frames`: Deduplicated frames with perceptual hashes (BLOB storage)
- `timeline`: Central temporal index mapping timestamps to frames/transcriptions
- `transcriptions`: Whisper-generated audio segments
- `timeframe_annotations`: User and AI-generated annotations
- `streams`: Active streaming sessions with metadata

## Processing Pipelines

### Video Processing
1. Validate filename format (`YYYY-MM-DD_HH-MM-SS.mp4`)
2. Extract UTC timestamp from filename
3. Extract frames at configured intervals (default 5 seconds)
4. Apply perceptual hashing for deduplication
5. Extract and transcribe audio with Whisper
6. Store all data with absolute UTC timestamps

### Stream Processing (nginx-rtmp Architecture)
1. Create stream session via API (returns RTMP URL + stream key)
2. OBS connects to nginx-rtmp container on port 1935
3. nginx-rtmp validates stream key via HTTP callback to backend
4. nginx's `exec_push` runs `stream_handler.py` which extracts frames via FFmpeg
5. Frames are POSTed to backend's `/api/streams/{stream_key}/frame` endpoint
6. Backend applies same deduplication as video processing
7. When OBS disconnects, nginx notifies backend via `on_publish_done` callback

## API Endpoints

### Core Operations
- `POST /api/capture`: Process video file
- `GET /api/search`: Universal data retrieval (time ranges, pagination)
- `GET /api/status`: System monitoring

### Annotations
- `GET /api/annotations/{annotation_id}`: Retrieve annotation
- `POST /api/annotations`: Create annotation
- `PUT /api/annotations/{annotation_id}`: Update annotation
- `DELETE /api/annotations/{annotation_id}`: Delete annotation

### Streaming
- `POST /api/streams/create`: Create new stream session (returns RTMP URL + stream key)
- `GET /api/streams`: List all streams
- `GET /api/streams/{stream_key}`: Get stream details
- `POST /api/streams/{stream_key}/stop`: Stop stream
- `DELETE /api/streams/{stream_key}`: Delete stream session

### RTMP Callbacks (internal - called by nginx-rtmp)
- `POST /api/streams/rtmp-callback/publish`: Validates stream key when OBS connects
- `POST /api/streams/rtmp-callback/publish-done`: Handles stream disconnection
- `POST /api/streams/rtmp-callback/play`: Allows playback
- `POST /api/streams/rtmp-callback/play-done`: Handles playback end
- `POST /api/streams/{stream_key}/frame`: Receives frames from nginx's exec_push script

## Testing

### Backend Testing
```bash
# Run all tests
uv run pytest tests/

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html

# Run specific test categories
uv run pytest tests/ -m unit
uv run pytest tests/ -m integration

# Test files
tests/test_db.py              # Database operations
tests/test_models.py           # Pydantic models
tests/test_frame.py            # Frame processing and deduplication
tests/test_api_services.py    # API service layer
tests/test_extractor.py       # Video extraction (if exists)
tests/test_transcriber.py     # Whisper transcription (if exists)
tests/conftest.py              # Shared fixtures

# Manual API testing
curl -X POST http://localhost:8000/api/capture \
  -H "Content-Type: application/json" \
  -d '{"filepath": "/path/to/2025-08-22_14-30-45.mp4"}'

curl "http://localhost:8000/api/search?type=timeline&limit=10"
curl "http://localhost:8000/api/status"
```

### Frontend Testing
```bash
# Run tests
npm run test

# With UI
npm run test:ui

# E2E tests (when available)
npm run test:e2e
```

## Configuration

### Backend (`config.yaml`)
```yaml
database:
  path: /data/db/mem.duckdb

sttd:
  host: "mem-sttd"              # STTD server host (use 127.0.0.1 for local dev)
  port: 8765                    # STTD server port
  timeout: 300.0                # Request timeout in seconds

capture:
  frame:
    interval_seconds: 5         # Extract frame every N seconds
    jpeg_quality: 85            # JPEG compression quality (1-100)
    enable_deduplication: true
    similarity_threshold: 100.0
  audio:
    chunk_duration_seconds: 300 # Audio chunks for transcription
    sample_rate: 16000

api:
  host: "0.0.0.0"
  port: 8000
  max_upload_size: 5368709120   # 5GB

streaming:
  rtmp:
    enabled: true
    host: localhost             # External hostname for RTMP URLs (override with RTMP_HOST env var)
    port: 1935
    max_concurrent_streams: 10
  capture:
    frame_interval_seconds: 1   # More frequent for live streams
```

### Docker Environment Variables
```bash
# GPU Configuration (for STTD service)
NVIDIA_VISIBLE_DEVICES=0        # GPU device ID
CUDA_VISIBLE_DEVICES=0          # CUDA device selection

# Application
MEM_CONFIG_PATH=/app/config/config.yaml  # Config file location
PYTHONUNBUFFERED=1             # Ensure logs are shown in real-time
LOG_LEVEL=INFO                 # Logging level

# Streaming
RTMP_HOST=localhost            # External hostname for RTMP URLs (e.g., aria.tap for remote access)

# Backend API
BACKEND_URL=http://mem-backend:8000  # For inter-service communication

# Docker Compose
COMPOSE_PROFILES=gpu           # or "cpu" for CPU-only mode
TAG=latest                     # Image version tag
```

### Frontend
- Development proxy configured in `vite.config.ts`
- API base URL: `http://localhost:8000`
- Frontend dev server: `http://localhost:5173`

## Performance Characteristics

- **Storage**: ~120MB per 24 hours (vs 2.4GB raw)
- **Query Performance**: <100ms for time-range searches
- **Deduplication**: 95% reduction for static scenes
- **Stream Processing**: Real-time with 1-second latency
- **Max Concurrent Streams**: 10 (configurable)
- **Supported Resolutions**: 360p to 8K

## Dependencies

### Python (requires 3.10-3.12)
Key packages:
- `fastapi` & `uvicorn`: REST API framework
- `duckdb`: High-performance columnar database
- `opencv-python-headless`: Video frame extraction
- `imagehash`: Perceptual hashing for deduplication
- `pydantic`: Data validation and serialization
- `httpx`: HTTP client for STTD communication
- `python-multipart`: File upload support
- `ffmpeg-python`: FFmpeg wrapper for audio extraction

### System Dependencies (provided by Nix)
- Python 3.10+
- FFmpeg (for audio/video processing)
- DuckDB CLI tools

### External Services
- **STTD**: Speech-to-text with diarization service (GPU or CPU mode)
  - Runs as separate container
  - Handles Whisper transcription and speaker identification

### Frontend
- `react` & `react-dom`: UI framework
- `@tanstack/react-query`: Data fetching
- `axios`: HTTP client
- `tailwindcss`: Styling
- `vite`: Build tool
- `vitest`: Testing