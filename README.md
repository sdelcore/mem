# Mem - Video Frame and Transcription Capture System

Mem is a focused data capture system that extracts frames and transcriptions from video files, storing them with absolute UTC timestamps in a SQLite database. The system enforces strict filename conventions and separates data capture from analysis.

## Core Features

- 📸 **Frame Extraction**: Captures frames at configurable intervals (default 5 seconds)
- 🎤 **Audio Transcription**: Transcribes audio in chunks using OpenAI Whisper
- ⏰ **UTC Timestamps**: All data stored with absolute UTC timestamps
- 💾 **BLOB Storage**: Images stored directly in database as BLOBs
- 📝 **Strict Format**: Enforces `YYYY-MM-DD_HH-MM-SS.mp4` filename format
- 🔍 **Time-based Queries**: Query frames and transcriptions by time range

## Quick Start

### Prerequisites

- Python 3.9+ 
- uv package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- FFmpeg for audio extraction
- 4GB+ RAM for Whisper models

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd mem
```

2. Install dependencies with uv:
```bash
uv sync
```

3. Initialize the database:
```bash
uv run mem reset-db --confirm
```

## Usage

### Video Filename Format

**REQUIRED FORMAT**: All video files must be named as `YYYY-MM-DD_HH-MM-SS.mp4`

Example: `2025-08-22_14-30-45.mp4`

This timestamp represents when the recording started in UTC.

### Command Line Interface

#### Process a single video:
```bash
uv run mem capture path/to/2025-08-22_14-30-45.mp4
```

Options:
- `--frame-interval 5` - Seconds between frame extraction (default: 5)
- `--chunk-duration 300` - Audio chunk size in seconds (default: 300 = 5 minutes)
- `--quality 85` - JPEG quality 1-100 (default: 85)
- `--whisper-model base` - Whisper model size: tiny/base/small/medium/large
- `--db mem.db` - Database path

#### Process multiple videos:
```bash
uv run mem batch path/to/videos --pattern "*.mp4"
```

#### View captured data:
```bash
# List frames from the last 24 hours
uv run mem list-frames

# List frames from a specific time range
uv run mem list-frames --start "2025-08-22T10:00:00" --end "2025-08-22T11:00:00"

# List transcriptions
uv run mem list-transcripts --source-id 1

# Export a frame as image
uv run mem export-frame --frame-id 1 --output frame.jpg
```

#### Database management:
```bash
# Show statistics
uv run mem stats

# Reset database (delete all data)
uv run mem reset-db --confirm
```

## Database Schema

### Core Tables

**sources** - Video/stream sources
- `id` - Primary key
- `type` - 'video', 'stream', or 'upload'
- `filename` - Original filename
- `start_timestamp` - UTC timestamp when recording started
- `end_timestamp` - UTC timestamp when recording ended
- `duration_seconds` - Total duration
- `frame_count` - Number of frames extracted

**frames** - Extracted video frames
- `id` - Primary key
- `source_id` - Reference to source
- `timestamp` - Absolute UTC timestamp
- `image_data` - BLOB containing JPEG image
- `width`, `height` - Frame dimensions
- `format` - Image format (usually 'jpeg')
- `size_bytes` - Size of image data

**transcriptions** - Audio transcriptions
- `id` - Primary key
- `source_id` - Reference to source
- `start_timestamp` - UTC start time
- `end_timestamp` - UTC end time
- `text` - Transcribed text
- `confidence` - Confidence score
- `language` - Detected language
- `word_count` - Number of words

### Post-Processing Tables (Future)

**frame_analysis** - Vision model analysis results
**transcript_analysis** - Text analysis results

## Architecture

```
mem/
├── src/
│   ├── capture/         # Core capture modules
│   │   ├── extractor.py # Frame extraction & timestamp parsing
│   │   ├── transcriber.py # Whisper transcription
│   │   └── pipeline.py  # Main processing pipeline
│   ├── storage/         # Database operations
│   │   ├── db.py       # SQLite operations
│   │   ├── models.py   # Pydantic models
│   │   └── schema.sql  # Database schema
│   └── cli.py          # Command-line interface
├── scripts/
│   └── create_test_video.py # Test video generator
└── docs/
    ├── API.md          # Planned REST API
    └── ARCHITECTURE.md # System design
```

## Processing Flow

1. **Validate** - Check filename format `YYYY-MM-DD_HH-MM-SS.mp4`
2. **Parse** - Extract UTC timestamp from filename
3. **Extract Frames** - Capture frames at intervals, convert to JPEG
4. **Extract Audio** - Export audio track using FFmpeg
5. **Transcribe** - Process audio in 5-minute chunks with Whisper
6. **Store** - Save frames as BLOBs and transcriptions with UTC timestamps

## Development

### Code Quality
```bash
make lint    # Run linting with ruff
make format  # Auto-format code with black and ruff
make clean   # Clean build artifacts
```

### Database Queries

```python
from src.storage.db import Database
from datetime import datetime, timedelta

db = Database("mem.db")
db.connect()

# Query frames by time range
start = datetime(2025, 8, 22, 10, 0, 0)
end = datetime(2025, 8, 22, 11, 0, 0)
frames = db.get_frames_by_time_range(start, end)

# Get transcriptions
transcripts = db.get_transcriptions_by_time_range(start, end)

db.disconnect()
```

## Limitations

- Only accepts videos with `YYYY-MM-DD_HH-MM-SS.mp4` filename format
- Images stored as BLOBs (database size grows with video content)
- Audio must be extractable with FFmpeg
- Requires Whisper models to be downloaded

## Future Enhancements

- REST API for remote access
- Separate processing pipeline for vision/text analysis
- Stream capture support
- Video upload endpoint
- Export functionality for bulk data

## License

MIT License - see LICENSE file for details