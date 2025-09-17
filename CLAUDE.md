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
uv run uvicorn src.api.app:app --reload --port 8000  # Start API server
uv run pytest tests/                            # Run all tests
uv run pytest tests/test_db.py -v              # Run specific test file
uv run pytest tests/test_api_services.py -v    # Test API services
uv run pytest -k "test_name" -v                 # Run specific test by name
make format                                      # Format code with black and ruff
make lint                                        # Run ruff linter
make clean                                       # Clean build artifacts
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

## Architecture

### Core Design Principles
- **Temporal Architecture**: All data anchored to absolute UTC timestamps
- **Storage Optimization**: Perceptual hashing achieves ~95% deduplication for static scenes
- **Strict Input Format**: Videos must be named `YYYY-MM-DD_HH-MM-SS.mp4`
- **Database Storage**: Frames stored as BLOBs in DuckDB, no external dependencies
- **Stream Support**: RTMP streams from OBS Studio with auto-resolution detection

### Backend Structure (`mem/src/`)
```
api/
├── app.py           # FastAPI application setup
├── routes.py        # API endpoints
├── services.py      # Business logic layer
└── models.py        # Request/response schemas

capture/
├── pipeline.py      # Main processing orchestrator
├── extractor.py     # Frame extraction, timestamp parsing
├── transcriber.py   # Whisper audio transcription
├── frame.py         # Perceptual hashing, deduplication
└── stream_server.py # RTMP streaming support

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

### Stream Processing
1. Create stream session with unique key
2. Start RTMP server on port 1935
3. Auto-detect stream resolution from first frame
4. Extract frames at 1 fps (configurable)
5. Apply same deduplication as video processing
6. Store frames in real-time

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
- `POST /api/streams/create`: Create new stream session
- `GET /api/streams`: List all streams
- `GET /api/streams/{stream_key}`: Get stream details
- `POST /api/streams/{stream_key}/start`: Start stream reception
- `POST /api/streams/{stream_key}/stop`: Stop stream
- `DELETE /api/streams/{stream_key}`: Delete stream session

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
tests/test_frame.py            # Frame processing
tests/test_api_services.py    # API service layer
tests/conftest.py              # Shared fixtures
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
  path: "mem.duckdb"

capture:
  frame_interval_seconds: 5
  jpeg_quality: 85

whisper:
  model: "base"

api:
  host: "0.0.0.0"
  port: 8000

streaming:
  rtmp:
    enabled: true
    port: 1935
    max_concurrent_streams: 10
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

### Python (requires 3.9)
Key packages:
- `fastapi` & `uvicorn`: REST API
- `duckdb`: Database engine
- `opencv-python-headless`: Video processing
- `openai-whisper`: Audio transcription
- `imagehash`: Perceptual hashing
- `pydantic`: Data validation

### Frontend
- `react` & `react-dom`: UI framework
- `@tanstack/react-query`: Data fetching
- `axios`: HTTP client
- `tailwindcss`: Styling
- `vite`: Build tool
- `vitest`: Testing