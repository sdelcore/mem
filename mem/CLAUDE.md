# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mem is a simplified data capture system that extracts frames and transcriptions from video files. It enforces strict filename conventions (`YYYY-MM-DD_HH-MM-SS.mp4`) and stores all data with absolute UTC timestamps. The core principle is separation of capture from analysis - first store raw data (frames as BLOBs and transcriptions), then process separately.

## Development Environment

### Database Initialization
The database (`mem.duckdb`) is automatically created and initialized on first API startup. No manual setup required!

### Nix Development Shell
This project uses Nix for a reproducible development environment. The shell includes Python, FFmpeg, DuckDB, and all necessary tools.

```bash
# Enter the development environment
nix develop

# Or run commands directly with nix develop
nix develop -c uv run uvicorn src.api.app:app --reload
```

### Using uv for Python Package Management
**IMPORTANT**: Always use `uv run` to execute Python commands to ensure dependencies are available:

```bash
# Wrong - will fail with missing dependencies
python src/api/app.py

# Correct - uses virtual environment with dependencies
uv run uvicorn src.api.app:app --reload

# Or with nix develop wrapper
nix develop -c uv run uvicorn src.api.app:app --reload
```

### Essential Commands
```bash
# Install/sync dependencies
uv sync

# Add a new dependency
uv add package-name

# Start API server
uv run uvicorn src.api.app:app --reload --port 8000

# Process a video via API
curl -X POST http://localhost:8000/api/capture \
  -H "Content-Type: application/json" \
  -d '{"filepath": "/path/to/2025-08-22_14-30-45.mp4"}'

# View captured data via API
curl "http://localhost:8000/api/search?type=timeline"
curl "http://localhost:8000/api/status"

# Run tests
nix develop -c uv run python tests/test_models.py
nix develop -c uv run python tests/test_db.py
nix develop -c uv run python tests/test_frame.py

# Run unit tests
uv run pytest tests/

# Code quality
make lint                   # Run ruff linting
make format                 # Auto-format with black and ruff

# Development workflow
make format && make lint   # Format and lint before commit
```

### Why nix develop and uv run?
- **nix develop**: Provides the complete development environment with system dependencies (Python, FFmpeg, etc.)
- **uv run**: Ensures Python code runs with the project's virtual environment and installed packages
- **Combined**: `nix develop -c uv run` gives you both system and Python dependencies

## Architecture

### Core Principle
**Capture first, process later**: The system captures raw data (frames and transcriptions) and stores them with UTC timestamps. Any analysis or processing happens separately on already-stored data.

### Key Modules

- `src/capture/` - Core capture functionality
  - `extractor.py` - Frame extraction, timestamp parsing, video info
  - `transcriber.py` - Whisper audio transcription
  - `pipeline.py` - Main processing pipeline that orchestrates capture
  - `frame.py` - Frame processing with perceptual hashing for deduplication

- `src/storage/` - Database operations
  - `db.py` - DuckDB database operations
  - `models.py` - Pydantic models for data structures
  - `schema.sql` - Database schema definition

- `src/api/` - FastAPI backend
  - `app.py` - Application setup
  - `routes.py` - API endpoints
  - `services.py` - Business logic
  - `models.py` - Request/response schemas

### Database Schema (DuckDB)

**Core Tables:**
- `sources` - Video/stream sources with UTC timestamps
- `unique_frames` - Deduplicated frames with perceptual hashing, stored as BLOBs
- `timeline` - Maps every timestamp to its frame and transcription data
- `transcriptions` - Audio transcriptions with UTC time ranges

**Key Features:**
- Uses DuckDB for better time-series performance
- Perceptual hashing for ~90% storage reduction via frame deduplication
- Timeline table provides temporal index for all data
- Native TIME_BUCKET and ASOF joins for temporal queries

### Processing Flow

1. **Validate filename**: Must be `YYYY-MM-DD_HH-MM-SS.mp4`
2. **Parse timestamp**: Extract UTC datetime from filename
3. **Create source**: Register video in database
4. **Extract frames**: Every N seconds, convert to JPEG, store as BLOB
5. **Extract audio**: Use FFmpeg to get audio track
6. **Transcribe**: Process in 5-minute chunks with Whisper
7. **Store**: Save everything with absolute UTC timestamps

## Development Standards

### Python Version
- **Required**: Python 3.10-3.12 (specified in pyproject.toml as `>=3.10,<3.13`)

### Code Quality
- Type hints required for all functions
- Docstrings for public functions
- Black formatting (line length 100)
- Ruff linting must pass

### Key Patterns

**Timestamp Handling:**
```python
# Parse from filename
from src.capture.extractor import parse_video_timestamp
timestamp = parse_video_timestamp("2025-08-22_14-30-45.mp4")

# All timestamps stored as UTC
from datetime import datetime
now_utc = datetime.utcnow()
```

**Database Operations:**
```python
from src.storage.db import Database

db = Database("mem.duckdb")
db.connect()
db.initialize()  # Create schema if needed

# Store unique frame with metadata
from src.storage.models import UniqueFrame
unique_frame = UniqueFrame(
    source_id=1,
    first_seen_timestamp=datetime.utcnow(),
    last_seen_timestamp=datetime.utcnow(),
    perceptual_hash="abc123",
    image_data=jpeg_bytes,  # Store as BLOB
    metadata={
        "jpeg_quality": 85,
        "width": 640,
        "height": 480
    }
)
frame_id = db.store_unique_frame(unique_frame)

db.disconnect()
```

**Frame Storage:**
```python
# Frames are stored as JPEG BLOBs, not file paths
from src.capture.extractor import frame_to_jpeg
jpeg_bytes = frame_to_jpeg(numpy_frame, quality=85)
# Store jpeg_bytes directly in database
```

## Configuration

### Database Settings
- Engine: DuckDB (high-performance columnar database)
- Default Path: `mem.duckdb`
- Features: Time-series optimized, columnar storage, native temporal functions

### Capture Settings (config.yaml)
- Frame interval: 5 seconds
- Audio chunk duration: 300 seconds (5 minutes)
- JPEG quality: 85
- Whisper model: base
- Frame deduplication: Enabled (95% similarity threshold)

### Environment Variables
- None currently used (simplified from previous version)

## Current State & Known Issues

### What's Working
- DuckDB database with time-series optimizations
- Frame deduplication with perceptual hashing (~90% storage reduction)
- Timeline-based temporal indexing
- Filename validation and timestamp parsing
- Frame extraction and JPEG conversion
- Audio extraction with FFmpeg
- Whisper transcription
- REST API for capture and data retrieval
- Test coverage for models, database, and deduplication

### What's Not Implemented Yet
- REST API endpoints
- Post-processing pipeline
- Stream capture (partially implemented but not exposed in API)
- Vision model analysis
- Text summarization

### Known Limitations
- Only accepts `YYYY-MM-DD_HH-MM-SS.mp4` filename format
- Stores images as BLOBs (mitigated by deduplication)
- DuckDB specific: No CASCADE foreign keys, no partial indexes
- Frame deduplication integrated in pipeline but may need tuning

## Testing

### Running Tests
```bash
# Run individual test files
nix develop -c uv run python tests/test_models.py
nix develop -c uv run python tests/test_db.py
nix develop -c uv run python tests/test_frame.py

# Run unit tests
uv run pytest tests/

```

### Test Coverage
- **test_models.py**: Tests for all Pydantic models (Source, UniqueFrame, Timeline, Transcription, etc.)
- **test_db.py**: Tests for DuckDB database operations (create, read, update, delete)
- **test_frame.py**: Tests for frame processing, perceptual hashing and deduplication logic

### Manual Testing
```bash
# Start API server
uv run uvicorn src.api.app:app --reload

# Process a video
curl -X POST http://localhost:8000/api/capture \
  -H "Content-Type: application/json" \
  -d '{"filepath": "/path/to/2025-08-22_14-30-45.mp4"}'

# Check results
curl http://localhost:8000/api/status
curl "http://localhost:8000/api/search?type=timeline"
curl "http://localhost:8000/api/search?type=frame&frame_id=1" --output frame.jpg
```

## Common Issues & Solutions

- **Invalid filename**: Videos must be named `YYYY-MM-DD_HH-MM-SS.mp4`
- **FFmpeg not found**: Use `nix develop` to ensure FFmpeg is available
- **Whisper model download**: First run will download models (~100MB+)
- **Out of memory**: Use smaller Whisper model (tiny or base)
- **API not starting**: Ensure port 8000 is available or specify different port

## Future Development

The system is designed for extensibility:
1. Capture pipeline stores raw data
2. Processing APIs will analyze stored data
3. Complete separation allows multiple processing passes
4. Can add new analysis types without touching capture code