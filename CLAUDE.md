# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mem is a video processing system that extracts frames and transcriptions from video files, storing them with absolute UTC timestamps in a DuckDB database. The architecture follows "capture first, process later" principle with ~90% storage reduction through perceptual hash deduplication.

## Development Commands

### Backend (Python/FastAPI)
```bash
cd mem/
uv sync                                          # Install dependencies
uv run uvicorn src.api.app:app --reload --port 8000  # Start API server
make format                                      # Format code with black
make lint                                        # Run ruff linter
uv run pytest tests/                            # Run all tests
uv run pytest tests/test_db.py -v              # Run specific test file
uv run pytest -k "test_name" -v                 # Run specific test
```

### Frontend (React/TypeScript)
```bash
cd mem-ui/
npm install                                      # Install dependencies
npm run dev                                      # Start dev server (port 5173)
npm run test                                     # Run tests
npm run build                                    # Build for production
npm run lint                                     # Run ESLint
```

### Full Stack
```bash
./start-mem.sh                                   # Start backend and frontend
./stop-mem.sh                                    # Stop all services
```

## Architecture

### Core Design Principles
- **Temporal Architecture**: All data anchored to absolute UTC timestamps from video filenames
- **Storage Optimization**: Perceptual hashing achieves ~95% deduplication for static scenes
- **Strict Input Format**: Videos must be named `YYYY-MM-DD_HH-MM-SS.mp4`
- **Database Storage**: Frames stored as BLOBs in DuckDB, no external dependencies

### Backend Structure (`mem/src/`)
- `api/`: FastAPI application, routes, services, and request/response models
- `capture/`: Video processing pipeline (frame extraction, perceptual hashing, transcription)
- `storage/`: DuckDB database layer with Pydantic models
- `config.py`: Centralized configuration management

### Frontend Structure (`mem-ui/src/`)
- `components/`: React components (Timeline, Search, Content viewer, Upload)
- `hooks/`: Custom React hooks for data fetching and state management
- `utils/`: Utility functions and API client

### Database Schema (DuckDB)
Key tables with temporal indexing:
- `sources`: Video/stream sources with UTC timestamps
- `unique_frames`: Deduplicated frames with perceptual hashes (BLOB storage)
- `timeline`: Central temporal index mapping timestamps to frames/transcriptions
- `transcriptions`: Whisper-generated audio segments
- `timeframe_annotations`: User and AI-generated annotations

## Video Processing Pipeline

1. Filename validation (`YYYY-MM-DD_HH-MM-SS.mp4` format required)
2. UTC timestamp extraction from filename
3. Frame extraction at 5-second intervals
4. Perceptual hashing for deduplication
5. Audio extraction and Whisper transcription
6. Storage with absolute UTC timestamps

## API Endpoints

- `POST /api/capture`: Process video file
- `GET /api/search`: Universal data retrieval (supports time ranges, pagination)
- `GET /api/status`: System monitoring
- `GET /api/annotations/{annotation_id}`: Retrieve annotation
- `POST /api/annotations`: Create annotation
- `PUT /api/annotations/{annotation_id}`: Update annotation
- `DELETE /api/annotations/{annotation_id}`: Delete annotation

## Testing Approach

Backend testing uses pytest with comprehensive fixtures in `tests/conftest.py`:
- Database operations (`test_db.py`)
- Data models (`test_models.py`)
- Frame processing (`test_frame.py`)
- API routes and services

Frontend testing uses Vitest with Testing Library for component testing.

## Configuration

Backend configuration via `config.yaml`:
- Database path and settings
- Frame extraction interval (5 seconds default)
- JPEG quality (85 default)
- Whisper model settings
- API host/port configuration

Frontend uses Vite proxy for API calls during development.

## Performance Characteristics

- Storage: ~120MB per 24 hours (vs 2.4GB raw)
- Query performance: <100ms for time-range searches
- Deduplication: 95% reduction for static scenes
- DuckDB columnar storage optimized for time-series analytics