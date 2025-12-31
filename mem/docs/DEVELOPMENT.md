# Development Guide

## Environment Setup

### Prerequisites
- Python 3.10-3.12
- FFmpeg for audio extraction
- STTD service (running on network)
- Nix package manager (optional, for reproducible environment)

### Quick Start
```bash
# Clone repository
git clone <repository-url>
cd mem

# Option 1: Using Nix (recommended for consistency)
nix develop

# Option 2: Using uv directly
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync

# Start API server
uv run uvicorn src.api.app:app --reload --port 8000

# Visit API docs
open http://localhost:8000/docs
```

### Development Commands
```bash
# Install dependencies
uv sync

# Add new dependency
uv add package-name

# Run tests
uv run pytest tests/ -v

# Code quality
make format  # Auto-format code
make lint    # Check code style
make clean   # Remove build artifacts

# Start API server
uv run uvicorn src.api.app:app --reload

# Process video via CLI (testing)
uv run python -m src.capture.pipeline /path/to/video.mp4
```

## Project Structure

```
mem/
├── src/
│   ├── api/            # FastAPI REST backend
│   │   ├── app.py      # Application setup & middleware
│   │   ├── routes.py   # API endpoint handlers
│   │   ├── services.py # Business logic layer
│   │   └── models.py   # Request/response schemas
│   │
│   ├── capture/        # Video processing core
│   │   ├── pipeline.py # Main orchestration
│   │   ├── extractor.py # Frame/audio extraction
│   │   ├── frame.py    # Deduplication logic
│   │   ├── transcriber.py # STTD client wrapper
│   │   ├── sttd_client.py # HTTP client for STTD service
│   │   └── stream_server.py # RTMP streaming management
│   │
│   ├── storage/        # Database layer
│   │   ├── db.py       # DuckDB operations
│   │   ├── models.py   # Pydantic models
│   │   └── schema.sql  # Database schema
│   │
│   └── config.py       # Configuration management
│
├── tests/              # Test suite
├── data/              # Runtime data
│   ├── uploads/       # Uploaded videos
│   ├── temp/          # Processing temp files
│   └── videos/        # Processed videos
│
├── config.yaml        # User configuration
└── mem.duckdb        # Database file
```

## Core Concepts

### Temporal Architecture
Everything is anchored to absolute UTC timestamps:
```python
from datetime import datetime
from src.capture.extractor import parse_video_timestamp

# Parse timestamp from filename
timestamp = parse_video_timestamp("2025-08-22_14-30-45.mp4")
# Returns: datetime(2025, 8, 22, 14, 30, 45, tzinfo=UTC)

# All database operations use UTC
now_utc = datetime.utcnow()
```

### Frame Deduplication
Using perceptual hashing for ~90% storage reduction:
```python
from src.capture.frame import FrameProcessor

processor = FrameProcessor(similarity_threshold=95.0)
is_duplicate = processor.is_duplicate(frame_data, previous_hash)
```

### Database Operations
```python
from src.storage.db import Database
from src.storage.models import Source

# Initialize database
db = Database("mem.duckdb")
db.connect()
db.initialize()  # Creates tables if needed

# Create a source
source = Source(
    type="video",
    filename="2025-08-22_14-30-45.mp4",
    start_timestamp=datetime.utcnow(),
    end_timestamp=datetime.utcnow(),
    metadata={"fps": 30, "width": 1920, "height": 1080}
)
source_id = db.create_source(source)

db.disconnect()
```

## Adding Features

### New API Endpoint
1. Define request/response models in `src/api/models.py`
2. Add route handler in `src/api/routes.py`
3. Implement business logic in `src/api/services.py`
4. Add tests in `tests/test_api_routes.py`

Example:
```python
# src/api/models.py
class ExportRequest(BaseModel):
    source_id: int
    format: Literal["json", "csv", "mp4"]

# src/api/routes.py
@router.post("/api/export")
async def export_data(request: ExportRequest):
    return export_service.export(request)

# src/api/services.py
class ExportService:
    def export(self, request: ExportRequest):
        # Implementation here
        pass
```

### New Processing Step
1. Create processor in `src/capture/`
2. Integrate into `pipeline.py`
3. Update database schema if needed
4. Add configuration options

### New Annotation Type
1. Add to `annotation_type` enum in schema
2. Update validation in `src/api/models.py`
3. Add processing logic if needed

## Testing

### Test Organization
```
tests/
├── conftest.py         # Shared fixtures
├── test_api_routes.py  # API endpoint tests
├── test_api_services.py # Business logic tests
├── test_db.py         # Database tests
├── test_frame.py      # Frame processing tests
├── test_models.py     # Model validation tests
└── test_*.py          # Other component tests
```

### Writing Tests
```python
import pytest
from src.storage.models import Source

def test_source_creation(test_db):
    """Test creating a source record."""
    source = Source(
        type="video",
        filename="test.mp4",
        start_timestamp=datetime.utcnow(),
        end_timestamp=datetime.utcnow()
    )
    source_id = test_db.create_source(source)
    assert source_id > 0
```

### Running Tests
```bash
# All tests
uv run pytest tests/

# Specific test file
uv run pytest tests/test_db.py

# With coverage
uv run pytest --cov=src --cov-report=html

# Specific test
uv run pytest tests/test_db.py::test_source_creation -v
```

## Code Standards

### Python Style
- Python 3.9 syntax only
- Type hints required for all functions
- Docstrings for public functions
- Black formatting (100 char lines)
- Ruff linting must pass

### Type Hints
```python
from typing import Optional, List, Dict, Any
from datetime import datetime

def process_video(
    filepath: str,
    start_time: Optional[datetime] = None,
    options: Dict[str, Any] = None
) -> List[int]:
    """Process a video file and return frame IDs."""
    pass
```

### Error Handling
```python
from fastapi import HTTPException

# API layer - use HTTPException
if not valid_file:
    raise HTTPException(status_code=400, detail="Invalid file format")

# Service layer - use custom exceptions
class ProcessingError(Exception):
    pass

# Database layer - let exceptions bubble up
try:
    result = db.execute(query)
except Exception as e:
    logger.error(f"Database error: {e}")
    raise
```

## Common Tasks

### Process Video Manually
```python
from src.capture.pipeline import VideoCaptureProcessor
from pathlib import Path

processor = VideoCaptureProcessor(
    db_path="mem.duckdb",
    config={"capture": {"frame": {"interval_seconds": 5}}}
)
result = processor.process_video(Path("video.mp4"))
print(f"Processed: {result['frames_extracted']} frames")
```

### Query Database
```python
from src.storage.db import Database
from datetime import datetime, timedelta

db = Database("mem.duckdb")
db.connect()

# Get recent frames
start = datetime.utcnow() - timedelta(hours=24)
end = datetime.utcnow()
frames = db.get_frames_by_time_range(start, end)

# Search transcripts
results = db.search_transcriptions("meeting", limit=10)

db.disconnect()
```

### Generate Test Data
```python
from tests.conftest import create_test_video

# Create test video with specific timestamp
video_path = create_test_video("2025-08-22_14-30-45.mp4")
```

## Debugging

### Enable Debug Logging
```python
# Set in config.yaml
logging:
  level: "DEBUG"

# Or via environment variable
export LOG_LEVEL=DEBUG
```

### Database Inspection
```bash
# Open database CLI
duckdb mem.duckdb

# Common queries
SELECT COUNT(*) FROM sources;
SELECT * FROM sources ORDER BY created_at DESC LIMIT 5;
SELECT COUNT(DISTINCT frame_id) as unique_frames FROM timeline;
```

### API Debugging
```bash
# Start with auto-reload
uv run uvicorn src.api.app:app --reload --log-level debug

# Test endpoints
curl -X POST http://localhost:8000/api/capture \
  -H "Content-Type: application/json" \
  -d '{"filepath": "/path/to/video.mp4"}' | jq '.'

# Check job status
curl http://localhost:8000/api/jobs/{job_id} | jq '.'
```

## Performance Profiling

### Memory Profiling
```python
from memory_profiler import profile

@profile
def process_large_video(filepath):
    # Function to profile
    pass
```

### Query Performance
```sql
-- Explain query plan
EXPLAIN SELECT * FROM timeline WHERE timestamp > ?;

-- Analyze table statistics
ANALYZE timeline;
```

## Contributing

### Before Submitting PR
1. Run `make format` to format code
2. Run `make lint` to check style
3. Add/update tests for changes
4. Update documentation if needed
5. Ensure all tests pass

### Commit Messages
```
feat: Add export API endpoint
fix: Correct timestamp parsing for DST
docs: Update API documentation
test: Add tests for frame deduplication
refactor: Simplify pipeline processing
```

## Known Issues

### Current Limitations
- Only accepts `YYYY-MM-DD_HH-MM-SS.mp4` format
- Synchronous video processing (blocks API)
- In-memory job tracking (lost on restart)
- No authentication implemented

### Common Problems
- **FFmpeg not found**: Install or use `nix develop`
- **STTD not available**: Start STTD server (`systemctl --user start sttd-server`)
- **Transcription fails**: Check STTD host/port in config.yaml
- **Slow processing**: Increase frame interval
- **Database locked**: Check for multiple writers

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [DuckDB Documentation](https://duckdb.org/docs/)
- [STTD (Speech-to-Text Daemon)](https://github.com/sdelcore/sttd)
- [Perceptual Hashing](https://github.com/JohannesBuchner/imagehash)