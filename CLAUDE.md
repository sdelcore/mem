# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mem is a simplified data capture system that extracts frames and transcriptions from video files. It enforces strict filename conventions (`YYYY-MM-DD_HH-MM-SS.mp4`) and stores all data with absolute UTC timestamps. The core principle is separation of capture from analysis - first store raw data (frames as BLOBs and transcriptions), then process separately.

## Development Commands

### Essential Commands
```bash
# Install dependencies
uv sync

# Initialize/reset database
uv run mem reset-db --confirm

# Run the CLI
uv run mem --help

# Process a video (must be named YYYY-MM-DD_HH-MM-SS.mp4)
uv run mem capture 2025-08-22_14-30-45.mp4

# View captured data
uv run mem list-frames
uv run mem list-transcripts
uv run mem stats

# Run tests
make test

# Code quality
make lint                   # Run ruff and mypy
make format                 # Auto-format with black and ruff

# Development workflow
make fmt && make test && make lint  # Full validation before commit
```

## Architecture

### Core Principle
**Capture first, process later**: The system captures raw data (frames and transcriptions) and stores them with UTC timestamps. Any analysis or processing happens separately on already-stored data.

### Key Modules

- `src/capture/` - Core capture functionality
  - `extractor.py` - Frame extraction, timestamp parsing, video info
  - `transcriber.py` - Whisper audio transcription
  - `pipeline.py` - Main processing pipeline that orchestrates capture

- `src/storage/` - Database operations
  - `db.py` - SQLite database operations
  - `models.py` - Pydantic models for data structures
  - `schema.sql` - Database schema definition

- `src/cli_new.py` - Command-line interface (will replace old cli.py)

### Database Schema

**Core Tables:**
- `sources` - Video/stream sources with UTC timestamps
- `frames` - Extracted frames stored as BLOBs with UTC timestamps
- `transcriptions` - Audio transcriptions with UTC time ranges

**Future Tables:**
- `frame_analysis` - Results from vision models
- `transcript_analysis` - Results from text analysis

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
- **Required**: Python 3.9 (specified in pyproject.toml as `>=3.9,<3.10`)

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

db = Database("mem.db")
db.connect()
db.initialize()  # Create schema if needed

# Store frame
frame = Frame(
    source_id=1,
    timestamp=datetime.utcnow(),
    image_data=jpeg_bytes,  # Store as BLOB
    width=640,
    height=480
)
frame_id = db.store_frame(frame)

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

### Capture Settings (hardcoded defaults, will move to config.yaml)
- Frame interval: 5 seconds
- Audio chunk duration: 300 seconds (5 minutes)
- JPEG quality: 85
- Whisper model: base

### Environment Variables
- None currently used (simplified from previous version)

## Current State & Known Issues

### What's Working
- Database schema creation
- Filename validation and timestamp parsing
- Frame extraction and JPEG conversion
- Audio extraction with FFmpeg
- Whisper transcription
- CLI commands for capture and viewing

### What's Not Implemented Yet
- REST API endpoints
- Post-processing pipeline
- Stream capture
- Vision model analysis
- Text summarization

### Known Limitations
- Only accepts `YYYY-MM-DD_HH-MM-SS.mp4` filename format
- Stores images as BLOBs (database can grow large)
- No config file support yet (uses hardcoded defaults)
- No tests written yet

## Testing

Currently no tests are implemented. The test hook warnings about missing test files can be ignored during this refactoring phase.

To test the system manually:
```bash
# Create test database
uv run mem reset-db --confirm --db test.db

# Process a video (must have correct filename)
uv run mem capture 2025-08-22_14-30-45.mp4 --db test.db

# Check results
uv run mem stats --db test.db
uv run mem list-frames --db test.db
```

## Common Issues & Solutions

- **Invalid filename**: Videos must be named `YYYY-MM-DD_HH-MM-SS.mp4`
- **FFmpeg not found**: Install FFmpeg for audio extraction
- **Whisper model download**: First run will download models (~100MB+)
- **Out of memory**: Use smaller Whisper model (tiny or base)

## Future Development

The system is designed for extensibility:
1. Capture pipeline stores raw data
2. Processing APIs will analyze stored data
3. Complete separation allows multiple processing passes
4. Can add new analysis types without touching capture code