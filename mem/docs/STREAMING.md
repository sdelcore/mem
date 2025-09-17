# OBS Studio Streaming Support

Mem now supports receiving multiple concurrent live streams from OBS Studio or any RTMP-compatible streaming software. The system automatically detects and adapts to any stream resolution, from 360p to 8K.

## Features

- **Multiple Concurrent Streams**: Support up to 10 simultaneous streams
- **Any Resolution**: Automatically adapts to stream resolution (360p to 8K)
- **Real-time Processing**: Frames extracted and stored with deduplication
- **Flexible Frame Rates**: Support for any frame rate (15-60+ fps)
- **Stream Management API**: Full REST API for stream control

## Quick Start

### 1. Start the Mem API Server

```bash
cd mem/
uv run uvicorn src.api.app:app --reload --port 8000
```

### 2. Create a Stream Session

```bash
# Create a new stream session
curl -X POST http://localhost:8000/api/streams/create \
  -H "Content-Type: application/json" \
  -d '{"name": "My Stream"}'

# Response:
{
  "session_id": "abc123...",
  "stream_key": "def456...",
  "status": "waiting",
  "rtmp_url": "rtmp://localhost:1935/live/def456..."
}
```

### 3. Configure OBS Studio

1. Open OBS Studio
2. Go to Settings → Stream
3. Set Service to "Custom"
4. Enter Server: `rtmp://localhost:1935/live`
5. Enter Stream Key: `{stream_key from step 2}`
6. Set your preferred video settings (any resolution works!)

### 4. Start Stream Reception

```bash
# Start the RTMP server for this stream
curl -X POST http://localhost:8000/api/streams/{stream_key}/start
```

### 5. Begin Streaming

Click "Start Streaming" in OBS Studio. The system will:
- Automatically detect stream resolution
- Extract frames at 1 fps (configurable)
- Apply deduplication (only stores changed frames)
- Store frames with timestamps

## API Endpoints

### Stream Management

#### Create Stream Session
```http
POST /api/streams/create
Content-Type: application/json

{
  "name": "Stream Name",
  "metadata": {"key": "value"}
}
```

#### List All Streams
```http
GET /api/streams
```

#### Get Stream Details
```http
GET /api/streams/{stream_key}
```

#### Start Stream Reception
```http
POST /api/streams/{stream_key}/start
```

#### Stop Stream
```http
POST /api/streams/{stream_key}/stop
```

#### Delete Stream Session
```http
DELETE /api/streams/{stream_key}
```

#### Get Streaming Server Status
```http
GET /api/streams/status
```

## Configuration

Edit `config.yaml` to customize streaming settings:

```yaml
streaming:
  rtmp:
    enabled: true
    port: 1935
    max_concurrent_streams: 10
  capture:
    frame_interval_seconds: 1  # How often to capture frames
    buffer_size: 30  # Buffer size in seconds
    max_frame_width: 7680  # Maximum allowed width (8K)
    max_frame_height: 4320  # Maximum allowed height (8K)
  auth:
    require_stream_key: true
```

## Supported Resolutions

The system automatically adapts to any resolution:

- **Standard**: 480p, 720p, 1080p
- **High Resolution**: 1440p, 4K (2160p)
- **Ultra High**: 5K, 6K, 8K
- **Aspect Ratios**: 16:9, 4:3, 21:9, 9:16 (vertical)
- **Custom**: Any resolution within safety limits

## How It Works

1. **RTMP Reception**: FFmpeg acts as an RTMP server listening on port 1935
2. **Frame Extraction**: Frames extracted as JPEG at configured intervals
3. **Auto-Detection**: Resolution detected from first frame
4. **Deduplication**: Only stores frames that differ from previous
5. **Storage**: Frames stored in DuckDB with metadata

## Example: Python Client

```python
import httpx
import asyncio

async def stream_example():
    async with httpx.AsyncClient() as client:
        # Create stream
        response = await client.post(
            "http://localhost:8000/api/streams/create",
            json={"name": "Python Stream"}
        )
        session = response.json()
        stream_key = session["stream_key"]
        
        print(f"Stream Key: {stream_key}")
        print(f"RTMP URL: {session['rtmp_url']}")
        
        # Start stream reception
        await client.post(f"http://localhost:8000/api/streams/{stream_key}/start")
        
        # Monitor stream
        while True:
            response = await client.get(f"http://localhost:8000/api/streams/{stream_key}")
            stream = response.json()
            if stream["status"] == "live":
                print(f"Live: {stream['resolution']}, Frames: {stream['frames_received']}")
            await asyncio.sleep(5)

asyncio.run(stream_example())
```

## Troubleshooting

### Stream Not Connecting
- Verify RTMP port 1935 is not in use: `lsof -i :1935`
- Check firewall settings allow port 1935
- Ensure FFmpeg is installed: `which ffmpeg`

### No Frames Being Stored
- Check deduplication settings in config.yaml
- Verify stream is actually changing (static content may be deduplicated)
- Check logs: frames may be skipped if identical

### OBS Connection Failed
- Verify server URL format: `rtmp://localhost:1935/live`
- Stream key must match exactly (no spaces)
- Try reducing video bitrate in OBS

### Performance Issues
- Reduce frame capture interval in config
- Lower OBS output resolution
- Check CPU/memory usage during streaming

## Architecture

```
OBS Studio → RTMP → FFmpeg Server → Frame Extraction → Deduplication → DuckDB
                                  ↓
                            Auto Resolution Detection
```

The streaming system integrates with Mem's existing architecture:
- Uses same frame deduplication system
- Stores in same DuckDB database
- Compatible with timeline queries
- Works with annotation system

## Security Notes

- Stream keys are UUID4 (cryptographically secure)
- Each stream isolated to its own process
- Maximum stream limits prevent resource exhaustion
- Input validation on all frame sizes

## Future Enhancements

Planned improvements:
- WebRTC support for lower latency
- Audio transcription from live streams
- Real-time alerts on scene changes
- Stream recording to file
- Multi-bitrate adaptive streaming