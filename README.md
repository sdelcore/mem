# Mem

Video processing system that captures frames and transcriptions from video files and live streams, storing them with absolute UTC timestamps in DuckDB. Achieves ~95% storage reduction through perceptual hash deduplication.

## Features

- **Frame Deduplication** - Perceptual hashing reduces storage from ~2.4GB to ~120MB per day
- **Speaker Diarization** - Automatic speaker labeling with voice profile matching
- **Live Streaming** - RTMP server for OBS Studio and IP cameras
- **GPU Transcription** - CUDA-accelerated Whisper (runs locally, no cloud)
- **Temporal Queries** - All data anchored to UTC timestamps
- **Self-Contained** - Frames stored as BLOBs in DuckDB

## Quick Start

### Local Development

```bash
# Clone repository
git clone <repository-url>
cd mem

# Start full stack (backend + frontend)
./start-mem.sh

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Docker Deployment

```bash
# GPU mode (requires NVIDIA GPU for fast transcription)
docker compose --profile gpu up -d

# CPU mode (no GPU required, slower transcription)
docker compose --profile cpu up -d

# Services will be available at:
# Frontend: http://localhost
# Backend API: http://localhost:8000
# RTMP Stream: rtmp://localhost:1935/live
```

### Manual Setup

```bash
# Backend
cd mem
uv sync
uv run uvicorn src.api.app:app --reload --port 8000

# Frontend (new terminal)
cd mem-ui
npm install
npm run dev

# Access at http://localhost:5173
```

## Processing Videos

### Important: Filename Format
Videos **MUST** be named `YYYY-MM-DD_HH-MM-SS.mp4` (UTC timestamp when recording started)

```bash
# Process a video via API
curl -X POST http://localhost:8000/api/capture \
  -H "Content-Type: application/json" \
  -d '{"filepath": "/path/to/2025-08-22_14-30-45.mp4"}'

# Or use the web UI
# 1. Navigate to http://localhost:3000
# 2. Click the Upload button
# 3. Select your video file
```

## Live Streaming with OBS

The streaming system uses nginx-rtmp for RTMP ingestion with automatic frame extraction and deduplication.

### 1. Create Stream Session (Web UI)
- Open http://localhost:3000
- Click "Streams" button in header
- Click "Create New Stream"
- Note the **Server URL** and **Stream Key** displayed

### 2. Configure OBS Studio
- Settings → Stream
- Service: **Custom**
- Server: *(copy Server URL from UI, e.g., `rtmp://localhost:1935/live`)*
- Stream Key: *(copy Stream Key from UI)*

### 3. Start Streaming
- Click "Start Streaming" in OBS
- The stream automatically goes live when OBS connects
- Watch real-time stats and frame counts in the UI

### Remote Deployment
For deployments accessible from other machines, set the `RTMP_HOST` environment variable:
```bash
# In docker-compose or .env
RTMP_HOST=your-server.example.com
```
This ensures the UI displays the correct RTMP URL for OBS configuration.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Input Sources                       │
│  ┌────────────┐        ┌─────────────────────────┐  │
│  │Video Files │        │ RTMP Streams (OBS/IP)   │  │
│  └─────┬──────┘        └───────────┬─────────────┘  │
└────────┼───────────────────────────┼─────────────────┘
         │                           │
         │                           ▼
         │              ┌─────────────────────────────┐
         │              │     nginx-rtmp Container    │
         │              │  • Validates stream keys    │
         │              │  • Extracts frames (FFmpeg) │
         │              │  • HLS/DASH output          │
         │              └───────────┬─────────────────┘
         │                          │ HTTP callbacks
         ▼                          ▼
┌──────────────────────────────────────────────────────┐
│               Capture Pipeline                        │
│  ┌─────────────┐    ┌──────────────────────────┐   │
│  │Frame Extract│───▶│ Perceptual Hashing (95%  │   │
│  │  (5 sec)    │    │ deduplication)           │   │
│  └─────────────┘    └──────────────────────────┘   │
│  ┌─────────────┐    ┌──────────────────────────┐   │
│  │Audio Extract│───▶│ STTD Service (external)  │   │
│  │             │    │ Whisper + Diarization    │   │
│  └─────────────┘    └──────────────────────────┘   │
└────────────────────────┬─────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────┐
│              DuckDB Storage Layer                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ Tables:                                      │   │
│  │ • unique_frames (BLOB storage)              │   │
│  │ • timeline (temporal index)                 │   │
│  │ • transcriptions (with speaker labels)      │   │
│  │ • sources (videos/streams metadata)         │   │
│  └─────────────────────────────────────────────┘   │
└────────────────────┬─────────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────────────┐
│                  Access Layer                         │
│  ┌──────────┐   ┌──────────┐   ┌──────────────┐   │
│  │ REST API │   │  Web UI  │   │ Future: AI    │   │
│  │  (8000)  │   │  (3000)  │   │  Processing   │   │
│  └──────────┘   └──────────┘   └──────────────┘   │
└──────────────────────────────────────────────────────┘
```

## Development

### Prerequisites
- Python 3.10-3.12 (3.13+ not yet supported due to dependencies)
- Node.js 18+ and npm
- FFmpeg for audio/video processing
- CUDA toolkit (optional, for GPU acceleration)

### Development Commands

```bash
# Backend
cd mem
uv sync                     # Install dependencies
make format                 # Auto-format code
make lint                   # Run linters
uv run pytest tests/        # Run tests

# Frontend
cd mem-ui
npm install                 # Install dependencies
npm run dev                 # Start dev server
npm run test               # Run tests
npm run build              # Build for production

# Full Stack
./start-mem.sh             # Start everything
./stop-mem.sh              # Stop everything
```

### Using Nix (Recommended)
```bash
# Enter development environment with all dependencies
nix develop

# Run commands with guaranteed dependencies
nix develop -c uv run uvicorn src.api.app:app --reload
```

## Performance

| Metric | Value | Notes |
|--------|-------|-------|
| Storage Reduction | 95% | Via perceptual hashing |
| Daily Storage | ~120MB | For 24/7 recording |
| Query Latency | <100ms | Time-range searches |
| Frame Processing | 30 fps | On modern hardware |
| Stream Latency | <1 second | RTMP to database |
| Max Concurrent Streams | 10 | Configurable |

## Configuration

### Backend (`mem/config.yaml`)
```yaml
sttd:
  host: "mem-sttd"             # STTD server host
  port: 8765                   # STTD server port
  timeout: 300.0               # Request timeout

capture:
  frame:
    interval_seconds: 5        # Extract frame every N seconds
    jpeg_quality: 85           # JPEG compression (1-100)

streaming:
  rtmp:
    host: localhost            # External hostname for RTMP URLs (override with RTMP_HOST env var)
    port: 1935
    max_concurrent_streams: 10
```

### Environment Variables
```bash
RTMP_HOST=localhost            # External hostname shown in RTMP URLs (for remote access)
MEM_CONFIG_PATH=/app/config/config.yaml  # Config file location
LOG_LEVEL=INFO                 # Logging level
```

## Docker Production Deployment

### Production Deployment

```bash
# GPU mode (recommended for fast transcription)
docker compose --profile gpu up -d

# CPU mode (no GPU required)
docker compose --profile cpu up -d

# Or set profile in .env file
echo "COMPOSE_PROFILES=gpu" > .env
docker compose up -d
```

### GPU Requirements (for STTD service)
- NVIDIA GPU with CUDA support
- nvidia-docker runtime installed
- 4GB+ VRAM for optimal performance

## API

Interactive API documentation available at http://localhost:8000/docs

### Core Endpoints

```bash
# Process video
POST /api/capture
{"filepath": "/path/to/video.mp4"}

# Search timeline
GET /api/search?type=timeline&start=2025-01-01&end=2025-01-02

# Get system status
GET /api/status

# Stream management
POST /api/streams/create        # Create stream session, returns RTMP URL + stream key
GET /api/streams                # List all streams
POST /api/streams/{stream_key}/stop   # Stop active stream
DELETE /api/streams/{stream_key}      # Delete stream session
```

## Testing

```bash
# Run all tests
cd mem && uv run pytest tests/

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html

# Frontend tests
cd mem-ui && npm run test
```

## Project Structure

```
mem/
├── mem/                    # Backend (Python/FastAPI)
│   ├── src/
│   │   ├── api/           # REST API endpoints
│   │   ├── capture/       # Frame/audio extraction + STTD client
│   │   └── storage/       # DuckDB operations
│   └── tests/             # Unit tests
├── mem-ui/                 # Frontend (React/TypeScript)
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom hooks
│   │   └── utils/         # API client
│   └── tests/             # Frontend tests
├── rtmp/                   # nginx-rtmp streaming server
│   ├── nginx.conf          # RTMP server config with HTTP callbacks
│   └── stream_handler.py   # Frame extraction script (called by nginx)
└── docker-compose.yml      # Container orchestration (gpu/cpu profiles)
```

## Limitations

- Videos must follow `YYYY-MM-DD_HH-MM-SS.mp4` naming convention
- No built-in authentication (use reverse proxy)
- Synchronous video processing (async coming soon)
- Maximum 10 concurrent streams (configurable)

## License

MIT