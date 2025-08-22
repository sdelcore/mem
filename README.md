# Mem - AI-Powered Time-Series Work Tracking System

Mem is an intelligent work tracking system that processes video recordings and live streams into a time-series database, storing context and activity data in 5-minute intervals. This enables timeline-based views of your work history, automatic activity classification, audio transcription, and semantic search capabilities.

## Features

- ⏰ **Time-Series Database**: Store work context in 5-minute intervals for timeline views
- 🎬 **Multiple Input Sources**: Process videos, live streams, audio, or manual entries
- 📊 **Timeline Visualization**: Interactive timeline view with day/week/month perspectives
- 🎤 **Audio Transcription**: Automatic speech-to-text using OpenAI Whisper
- 🧠 **Work Classification**: AI-powered categorization of work activities
- 👁️ **Visual Analysis**: Frame-by-frame analysis to detect applications and context
- 🔍 **Semantic Search**: Find work sessions using natural language queries
- 📈 **Daily Summaries**: Automatic productivity tracking and project time allocation
- 📹 **Real-time Streaming**: Process live video from webcam or screen
- 💾 **Vector Search**: Semantic similarity search with embeddings

## Quick Start

### Prerequisites

- Python 3.9+ (3.9 recommended for compatibility)
- uv package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- 4GB+ RAM for AI models
- Webcam (optional, for live streaming)

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

3. Run the setup script to initialize database and download models:
```bash
uv run python setup.py
```

This will:
- ✅ Check all dependencies
- 📁 Create necessary directories
- 💾 Initialize the SQLite database
- 🎤 Download Whisper model for transcription
- 🧠 Download sentence transformer for embeddings

## Usage

### Command Line Interface

#### Process a single video:
```bash
uv run python -m src.cli process path/to/video.mp4
```

#### Process multiple videos in a directory:
```bash
uv run python -m src.cli batch path/to/videos --pattern "*.mp4" --concurrent 3
```

#### Stream from webcam:
```bash
uv run python -m src.cli stream --source webcam:0 --realtime
```

#### Search work sessions:
```bash
uv run python -m src.cli search "debugging the authentication module"
```

#### List recent sessions:
```bash
uv run python -m src.cli list-sessions --limit 10
```

#### View statistics:
```bash
uv run python -m src.cli stats
```

### Web Interface

Launch the timeline dashboard:
```bash
uv run streamlit run app_timeline.py
```

Then open http://localhost:8501 in your browser.

The timeline interface provides:
- 📊 **Timeline View**: Interactive visualization of work in 5-minute intervals
- 📅 **Multiple Views**: Day, week, month, or custom date range views
- 📤 **Video Upload**: Process videos into timeline entries
- 📈 **Analytics Dashboard**: Daily summaries and productivity metrics
- 📁 **Project Timeline**: Track time spent on specific projects
- 🔍 **Smart Filters**: Filter by work category or project name

## Project Structure

```
mem/
├── src/
│   ├── capture/        # Video/audio capture modules
│   │   ├── base.py     # Abstract base classes
│   │   ├── video.py    # Video file capture
│   │   ├── webcam.py   # Webcam capture
│   │   ├── audio.py    # Audio capture
│   │   └── factory.py  # Capture source factory
│   ├── processors/     # Frame and audio processing
│   │   ├── frame.py    # Frame extraction/processing
│   │   ├── audio.py    # Audio transcription (Whisper)
│   │   └── vision.py   # Visual analysis
│   ├── analysis/       # AI classification and embeddings
│   │   ├── classifier.py   # Work type classification
│   │   ├── embeddings.py   # Semantic embeddings
│   │   └── summarizer.py   # Content summarization
│   ├── database/       # Storage and retrieval
│   │   ├── manager.py      # Database operations
│   │   ├── timeseries_manager.py  # Time-series database ops
│   │   └── vector_ops.py   # Vector search operations
│   ├── pipeline/       # Processing orchestration
│   │   ├── process.py      # Video processing pipeline
│   │   ├── timeseries_processor.py  # Time-series processor
│   │   ├── chunker.py      # 5-minute interval chunking
│   │   ├── batch.py        # Batch processing
│   │   └── stream.py       # Real-time streaming
│   ├── models/         # Data models
│   │   ├── timeseries.py   # Time-series data models
│   │   ├── session.py      # Work session models
│   │   ├── activity.py     # Activity tracking
│   │   └── database.py     # Database schemas
│   └── cli.py         # Command-line interface
├── backend/           # FastAPI backend server
│   └── server.py      # API endpoints for timeline
├── tests/             # Unit and integration tests
├── app_timeline.py    # Streamlit timeline interface
├── setup.py          # Setup and initialization script
├── init_timeseries_db.py  # Time-series database init
└── pyproject.toml    # Project dependencies
```

## Configuration

### Processing Options

Configure processing parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `frame_interval` | 5s | How often to extract frames |
| `chunk_duration` | 30s | Audio chunk size for transcription |
| `whisper_model` | base | Model size (tiny/base/small/medium/large) |
| `batch_size` | 3 | Number of concurrent processes |
| `buffer_duration` | 60s | Stream buffer size |

### Work Categories

The AI classifier categorizes work into:

- **🚀 Productive**: Coding, writing, designing, documentation
- **📚 Learning**: Tutorials, courses, research, reading docs
- **👥 Meeting**: Video calls, presentations, discussions
- **⏸️ Wasted**: Social media, entertainment, browsing

## Advanced Features

### Vector Search

Use semantic search to find related sessions:

```python
from src.database.vector_ops import VectorOperations

vec_ops = VectorOperations("mem.db")
vec_ops.connect()

# Search by meaning, not just keywords
results = vec_ops.search_similar(
    "working on React components", 
    limit=5
)
```

### Custom Processing Pipeline

Create custom processing pipelines:

```python
from src.pipeline.process import VideoProcessor

processor = VideoProcessor(
    db_path="mem.db",
    frame_interval=10,  # Extract frame every 10 seconds
    enable_vision=True   # Enable visual analysis
)

result = await processor.process_video("video.mp4")
```

### Real-time Analysis

Enable real-time analysis during streaming:

```bash
# Stream with real-time classification
uv run python -m src.cli stream --realtime --buffer 60

# Stream from specific camera
uv run python -m src.cli stream --source webcam:1
```

### Batch Processing with Progress

Process multiple videos with progress tracking:

```python
from src.pipeline.batch import BatchProcessor

batch = BatchProcessor(
    db_path="mem.db",
    max_concurrent=5
)

def progress_callback(current, total, filename):
    print(f"[{current}/{total}] Processing: {filename}")

results = await batch.process_directory(
    "videos/",
    pattern="*.mp4",
    progress_callback=progress_callback
)
```

## Testing

Run the test suite:
```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html

# Run specific test categories
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v
```

## Troubleshooting

### Common Issues

#### 1. Whisper model download fails
```bash
# Manual download with SSL bypass (if needed)
uv run python -c "import ssl; ssl._create_default_https_context = ssl._create_unverified_context; import whisper; whisper.load_model('base')"
```

#### 2. SQLite-vec extension not found
The vector search feature requires the sqlite-vec extension. Without it, vector search is disabled but all other features work normally.

#### 3. Out of memory errors
- Use smaller Whisper model: `tiny` or `base`
- Reduce batch size in batch processing
- Process videos sequentially instead of parallel

#### 4. Video codec issues
Ensure ffmpeg is installed:
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

### Performance Optimization

| Optimization | Impact | How to Enable |
|-------------|--------|---------------|
| GPU Acceleration | 5-10x faster | Install CUDA-enabled PyTorch |
| Smaller Models | Less memory | Use `whisper_model="tiny"` |
| Frame Sampling | Faster processing | Increase `frame_interval` |
| Batch Processing | Better throughput | Use batch CLI command |
| Caching | Avoid reprocessing | Enable in embeddings |

### Debug Mode

Enable debug logging for troubleshooting:
```bash
# CLI with debug output
uv run python -m src.cli --debug process video.mp4

# Set environment variable
export MEM_DEBUG=1
```

## API Examples

### Python API

```python
import asyncio
from src.pipeline.process import VideoProcessor
from src.database.manager import DatabaseManager

async def main():
    # Initialize processor
    processor = VideoProcessor(db_path="mem.db")
    
    # Process video
    result = await processor.process_video("meeting.mp4")
    
    # Query results
    db = DatabaseManager("mem.db")
    db.connect()
    
    sessions = db.search_sessions("team standup")
    for session in sessions:
        print(f"Found: {session['created_at']} - {session['work_category']}")
    
    db.disconnect()

asyncio.run(main())
```

### REST API (Coming Soon)

Future versions will include a REST API for integration with other tools.

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests before committing (`uv run pytest`)
4. Follow the code style (run `uv run black src/`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/mem.git
cd mem

# Install in development mode
uv sync

# Run tests
uv run pytest

# Format code
uv run black src/
uv run isort src/
```

## License

MIT License - see LICENSE file for details

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for speech recognition
- [Sentence Transformers](https://www.sbert.net/) for semantic embeddings
- [Streamlit](https://streamlit.io/) for the web interface
- [Click](https://click.palletsprojects.com/) for the CLI framework
- [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation

## Support

- 📧 Email: support@mem-app.com
- 🐛 Issues: https://github.com/yourusername/mem/issues
- 💬 Discussions: https://github.com/yourusername/mem/discussions

---

Made with ❤️ by the Mem team