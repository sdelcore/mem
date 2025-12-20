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
# Start all services with Docker Compose
docker-compose up -d

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

### 1. Create Stream Session (Web UI)
- Open http://localhost:3000
- Click "Streams" button in header
- Click "Create New Stream"
- Copy the stream key

### 2. Configure OBS Studio
- Settings → Stream
- Service: **Custom**
- Server: `rtmp://localhost:1935/live`
- Stream Key: *(paste from UI)*

### 3. Start Streaming
- Click Play button on stream card in UI
- Start streaming in OBS
- Watch real-time stats and deduplication

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Input Sources                       │
│  ┌────────────┐        ┌─────────────────────────┐  │
│  │Video Files │        │ RTMP Streams (OBS/IP)   │  │
│  └─────┬──────┘        └───────────┬─────────────┘  │
└────────┼───────────────────────────┼─────────────────┘
         │                           │
         ▼                           ▼
┌──────────────────────────────────────────────────────┐
│               Capture Pipeline                        │
│  ┌─────────────┐    ┌──────────────────────────┐   │
│  │Frame Extract│───▶│ Perceptual Hashing (95%  │   │
│  │  (5 sec)    │    │ deduplication)           │   │
│  └─────────────┘    └──────────────────────────┘   │
│  ┌─────────────┐    ┌──────────────────────────┐   │
│  │Audio Extract│───▶│ Whisper Transcription    │   │
│  │             │    │ (GPU Accelerated)        │   │
│  └─────────────┘    └──────────────────────────┘   │
└────────────────────────┬─────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────┐
│              DuckDB Storage Layer                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ Tables:                                      │   │
│  │ • unique_frames (BLOB storage)              │   │
│  │ • timeline (temporal index)                 │   │
│  │ • transcriptions (Whisper output)           │   │
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
capture:
  frame_interval_seconds: 5    # Extract frame every N seconds
  jpeg_quality: 85             # JPEG compression (1-100)

whisper:
  model: "base"                # tiny/base/small/medium/large
  device: "cuda"               # cuda or cpu
  compute_type: "float16"      # float16 (GPU) or int8 (CPU)

streaming:
  rtmp:
    port: 1935
    max_concurrent_streams: 10
```

## Docker Production Deployment

### Production Deployment with GPU

```bash
# Build and push images
./deploy/build-and-push.sh

# Deploy to server
./deploy/deploy-to-wise18.sh

# Or manually with docker-compose
docker-compose -f docker-compose.yml up -d
```

### GPU Requirements
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
POST /api/streams/create
GET /api/streams
POST /api/streams/{stream_key}/start
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
│   │   ├── capture/       # Frame/audio extraction
│   │   └── storage/       # DuckDB operations
│   └── tests/             # Unit tests
├── mem-ui/                 # Frontend (React/TypeScript)
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom hooks
│   │   └── utils/         # API client
│   └── tests/             # Frontend tests
├── rtmp/                   # RTMP streaming server
├── deploy/                 # Deployment scripts
└── docker-compose.yml      # Container orchestration
```

## Limitations

- Videos must follow `YYYY-MM-DD_HH-MM-SS.mp4` naming convention
- No built-in authentication (use reverse proxy)
- Synchronous video processing (async coming soon)
- Maximum 10 concurrent streams (configurable)

## License

MIT