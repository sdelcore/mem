# Mem - Video Frame and Transcription Capture System

Mem is a video processing system that extracts frames and transcriptions from video files, storing them with absolute UTC timestamps in a time-series optimized DuckDB database.

## ✨ Key Features

- **Temporal Architecture**: All data anchored to absolute UTC timestamps
- **90% Storage Reduction**: Perceptual hash deduplication for frames
- **AI Transcription**: STTD service with speaker diarization
- **RTMP Streaming**: Live capture from OBS Studio
- **REST API**: FastAPI with interactive docs at `/docs`
- **Self-Contained**: Database stores frames as BLOBs, no external dependencies
- **Strict Format**: Videos must follow `YYYY-MM-DD_HH-MM-SS.mp4` naming

## 🚀 Quick Start

### Prerequisites
- Python 3.10-3.12
- FFmpeg for audio extraction
- STTD service for transcription (running on network)

### Installation
```bash
# Clone and setup
git clone <repository-url>
cd mem

# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Database auto-initializes on first run
```

### Start the Server
```bash
# Run API server
uv run uvicorn src.api.app:app --reload --port 8000

# Access at:
# http://localhost:8000/docs - Interactive API docs
# http://localhost:8000/api/status - System status
```

### Basic Usage
```bash
# Process a video
curl -X POST http://localhost:8000/api/capture \
  -H "Content-Type: application/json" \
  -d '{"filepath": "/path/to/2024-01-01_12-00-00.mp4"}'

# Search timeline (last 24 hours)
curl "http://localhost:8000/api/search?type=timeline"

# Get system status
curl http://localhost:8000/api/status
```

📖 **Full API documentation**: See [docs/API.md](docs/API.md)

## 📁 Video Filename Format

**Required**: `YYYY-MM-DD_HH-MM-SS.mp4` (UTC timestamp when recording started)

Example: `2025-08-22_14-30-45.mp4`

## 📚 Documentation

- **[API Reference](docs/API.md)** - Complete endpoint documentation
- **[Architecture](docs/ARCHITECTURE.md)** - System design and data flow
- **[Database Schema](docs/SCHEMA.md)** - Table structure and relationships
- **[Development](docs/DEVELOPMENT.md)** - Setup and contribution guide
- **[Operations](docs/OPERATIONS.md)** - Deployment and monitoring

## 🛠️ Development

```bash
# Code quality
make format  # Auto-format code
make lint    # Check style

# Run tests
uv run pytest tests/

# Enter Nix shell (optional)
nix develop
```

See [Development Guide](docs/DEVELOPMENT.md) for detailed instructions.

## ⚡ Performance

- **90% storage reduction** via perceptual hashing
- **Time-series optimized** DuckDB with native temporal functions
- **~120MB per day** storage for continuous capture
- **<100ms query latency** for time-range searches

## 🔒 Security & Privacy

- All processing happens locally (no cloud APIs)
- STTD transcription runs on your network
- Database can be encrypted at filesystem level
- No authentication in current version (see [Operations Guide](docs/OPERATIONS.md) for adding it)

## 📊 System Requirements

- **Storage**: ~120MB per 24 hours of video
- **RAM**: 4GB minimum (8GB recommended)
- **CPU**: 4+ cores recommended for faster processing
- **Disk**: SSD recommended for database performance

## 🚧 Current Limitations

- Videos must follow strict naming format
- No authentication (planned)
- Synchronous processing (async planned)
- In-memory job tracking (Redis planned)

## 📝 License

MIT License - see LICENSE file