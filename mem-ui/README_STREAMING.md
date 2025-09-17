# Streaming UI Feature Guide

## Overview

The Mem UI now includes comprehensive OBS Studio streaming support with a dedicated Stream Manager component that allows you to create, manage, and monitor multiple concurrent streams directly from the web interface.

## Features

### Stream Manager Button
Located in the header controls between the Search bar and Video Upload button, the Stream Manager provides:

- **Stream Counter Badge**: Shows active stream count with a pulsing red indicator
- **Dropdown Panel**: Click to expand the full stream management interface
- **Auto-refresh**: Updates stream status every 5 seconds when expanded

### Stream Management Interface

#### 1. Create New Stream
- Click "Create New Stream" button
- Optionally enter a stream name
- Receive unique RTMP URL and Stream Key
- Copy credentials with one click

#### 2. Stream Card Display
Each stream shows:
- **Status Indicator**: 
  - 🔴 Red pulse = Live streaming
  - 🟡 Yellow = Waiting for connection
  - ⚫ Gray = Stream ended
  - ❌ Red = Error state
- **Resolution**: Auto-detected from stream (e.g., 1920x1080)
- **Statistics**: Frame count, duration, start time
- **RTMP Details**: Server URL and unique stream key
- **Actions**: Start, Stop, Delete buttons

#### 3. Stream Controls
- **Start**: Begin receiving RTMP stream
- **Stop**: End active stream
- **Delete**: Remove stream session
- **Show/Hide Details**: Toggle RTMP configuration display
- **Copy**: One-click copy for RTMP URL and Stream Key

## How to Use

### Step 1: Create a Stream Session
1. Click the "Streams" button in the header
2. Click "Create New Stream"
3. Enter an optional name (e.g., "Main Camera")
4. Click "Create Stream"

### Step 2: Configure OBS Studio
1. Open OBS Studio
2. Go to Settings → Stream
3. Set Service: **Custom**
4. Server: `rtmp://localhost:1935/live`
5. Stream Key: *Copy from the UI using the copy button*
6. Apply settings

### Step 3: Start Streaming
1. In the Mem UI, click the Play button on your stream card
2. In OBS Studio, click "Start Streaming"
3. Watch the status change to Live with real-time stats

### Step 4: Monitor Your Stream
- **Live indicator**: Pulsing red dot shows active streaming
- **Frame stats**: See received vs stored frames (deduplication active)
- **Duration**: Live timer shows streaming duration
- **Resolution**: Automatically detected and displayed

### Step 5: Stop Streaming
1. Click the Stop button in the UI, or
2. Stop streaming in OBS Studio
3. Stream status changes to "Ended"

## Visual Indicators

### Button States
- **Forest Green**: Default state
- **Dark Green**: Hover/Active
- **Red Pulse**: Active streams indicator
- **Disabled**: Grayed out during operations

### Stream Status Colors
- **Red (Live)**: Currently streaming
- **Yellow (Waiting)**: Ready to receive stream
- **Gray (Ended)**: Stream finished
- **Red (Error)**: Connection or processing error

## Tips

1. **Multiple Streams**: Create multiple stream sessions for different cameras or sources
2. **Auto-sort**: Active streams appear at the top of the list
3. **Copy Feature**: Click copy icons to quickly grab RTMP details
4. **Frame Deduplication**: Only unique frames are stored (100% threshold)
5. **Any Resolution**: Supports any OBS output resolution from 360p to 8K

## Troubleshooting

### Stream Won't Start
- Ensure the backend API is running on port 8000
- Check that FFmpeg is installed
- Verify port 1935 is not blocked

### OBS Can't Connect
- Double-check the Stream Key matches exactly
- Ensure you clicked "Start" on the stream card first
- Try reducing bitrate in OBS settings

### No Frames Showing
- Check OBS is actually streaming (not just recording)
- Verify the stream status shows "Live"
- Look for movement in the video (static frames may be deduplicated)

## Architecture

```
OBS Studio → RTMP (1935) → FFmpeg → Frame Extraction → Deduplication → DuckDB
                                  ↓
                          UI Updates (WebSocket/Polling)
```

The streaming UI integrates seamlessly with the existing Mem interface, following the same design patterns and color scheme (forest green, cream, sage) while providing powerful stream management capabilities.