# OBS Studio Streaming Implementation

## Overview
The mem system now supports receiving live streams from OBS Studio via RTMP protocol. Multiple concurrent streams can be processed simultaneously with automatic frame extraction and deduplication.

## Architecture

### Components
1. **RTMP Server** (`src/capture/stream_server.py`)
   - Manages stream sessions with unique keys
   - Uses FFmpeg to receive RTMP streams
   - Extracts JPEG frames at configurable intervals
   - Auto-detects stream resolution

2. **Stream Processor** (`src/capture/pipeline.py::StreamCaptureProcessor`)
   - Processes incoming frames with perceptual hashing
   - Stores frames with 100% deduplication threshold
   - Creates source entries in database

3. **API Endpoints** (`src/api/routes.py`)
   - POST `/api/streams/create` - Create new stream session
   - GET `/api/streams` - List all streams
   - GET `/api/streams/{stream_key}` - Get stream details
   - POST `/api/streams/{stream_key}/start` - Start receiving stream
   - POST `/api/streams/{stream_key}/stop` - Stop stream
   - DELETE `/api/streams/{stream_key}` - Delete stream session

4. **Database Schema**
   - Added `stream_sessions` table for tracking live streams
   - Links to sources table via foreign key

## Configuration

### Backend (`config.yaml`)
```yaml
streaming:
  rtmp:
    enabled: true
    port: 1935
    max_concurrent_streams: 10
  capture:
    frame_interval_seconds: 1
    buffer_size: 30
    max_frame_width: 7680  # 8K support
    max_frame_height: 4320
```

### OBS Studio Setup
1. Settings → Stream
2. Service: Custom
3. Server: `rtmp://localhost:1935/live`
4. Stream Key: Copy from UI (UUID format)

## Usage Flow

1. **Create Stream Session**
   - Call `/api/streams/create` 
   - Returns unique stream_key and RTMP URL

2. **Configure OBS**
   - Enter RTMP server URL
   - Enter stream key
   - Configure video settings (any resolution supported)

3. **Start Receiving**
   - Call `/api/streams/{stream_key}/start`
   - Creates FFmpeg listener process

4. **Stream Data**
   - OBS sends RTMP stream
   - FFmpeg extracts JPEG frames
   - Frames deduplicated and stored in DuckDB

5. **Stop Stream**
   - Call `/api/streams/{stream_key}/stop`
   - Terminates FFmpeg process
   - Updates source end timestamp

## Features

### Frame Processing
- **Automatic Resolution Detection**: Detects frame dimensions from first received frame
- **Perceptual Hashing**: Uses dhash for frame deduplication
- **100% Deduplication**: Only stores frames that are completely different
- **JPEG Compression**: High quality (Q=2) frame extraction

### Session Management
- **UUID Stream Keys**: Secure, unique identifiers
- **Status Tracking**: waiting → live → ended/error
- **Frame Statistics**: Tracks received vs stored frames
- **Duration Calculation**: Automatic timestamp tracking

### Error Handling
- **Process Cleanup**: FFmpeg processes terminated on stop/error
- **Database Transactions**: Proper connection management
- **Timezone Handling**: Supports both naive and aware datetimes

## UI Integration

### React Components
- `StreamManager`: Main dropdown panel for stream management
- `StreamCard`: Individual stream display with controls
- `StreamControls`: Create new stream interface
- `useStreams`: React Query hooks for data fetching

### Features
- **Live Status Indicators**: Pulsing red dot for active streams
- **Copy to Clipboard**: One-click copy for RTMP URL and Stream Key
- **Auto-refresh**: Updates every 5 seconds when panel is open
- **Frame Statistics**: Shows deduplication effectiveness

## Testing

### Manual Testing
```bash
# Create stream
curl -X POST http://localhost:8000/api/streams/create \
  -H "Content-Type: application/json" \
  -d '{"stream_name": "Test Stream"}'

# Start stream
curl -X POST http://localhost:8000/api/streams/{stream_key}/start

# Configure OBS and start streaming

# Stop stream
curl -X POST http://localhost:8000/api/streams/{stream_key}/stop

# Check status
curl http://localhost:8000/api/streams/{stream_key}
```

### Verified Functionality
✅ Create multiple stream sessions
✅ Start/stop streams independently
✅ FFmpeg process management
✅ Frame extraction and storage
✅ Proper cleanup on stop
✅ UI controls working
✅ Copy to clipboard for credentials

## Known Limitations

1. **No Audio Capture**: Currently only processes video frames
2. **No Real-time Preview**: Frames stored but not displayed in timeline yet
3. **RTMP Only**: No support for other streaming protocols
4. **Local Only**: RTMP server only accepts localhost connections

## Future Enhancements

1. **Audio Transcription**: Add STTD processing for stream audio
2. **Real-time Display**: Show live frames in timeline
3. **Remote Streaming**: Accept streams from external sources
4. **Multiple Protocols**: Support RTSP, WebRTC
5. **Stream Recording**: Option to save full video file
6. **Bitrate Detection**: Auto-detect and display stream bitrate