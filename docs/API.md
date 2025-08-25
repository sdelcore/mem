# API Documentation

## Overview

The Mem API provides REST endpoints for querying captured frames and transcriptions by time range.

## Planned Endpoints

### Query Endpoints

#### GET /api/frames
Query frames by time range.

**Parameters:**
- `start` (ISO 8601 timestamp) - Start of time range (UTC)
- `end` (ISO 8601 timestamp) - End of time range (UTC)
- `source_id` (optional) - Filter by specific source
- `limit` (optional, default: 100) - Maximum frames to return

**Response:**
```json
{
  "frames": [
    {
      "id": 1,
      "source_id": 1,
      "timestamp": "2025-08-22T14:30:45Z",
      "width": 1920,
      "height": 1080,
      "format": "jpeg",
      "size_bytes": 125432
    }
  ],
  "total": 250,
  "returned": 100
}
```

#### GET /api/frames/{id}/image
Get the actual image data for a frame.

**Response:**
- Content-Type: image/jpeg
- Binary image data

#### GET /api/transcriptions
Query transcriptions by time range.

**Parameters:**
- `start` (ISO 8601 timestamp) - Start of time range (UTC)
- `end` (ISO 8601 timestamp) - End of time range (UTC)
- `source_id` (optional) - Filter by specific source
- `search` (optional) - Text search within transcriptions

**Response:**
```json
{
  "transcriptions": [
    {
      "id": 1,
      "source_id": 1,
      "start_timestamp": "2025-08-22T14:30:00Z",
      "end_timestamp": "2025-08-22T14:35:00Z",
      "text": "Transcribed text content...",
      "confidence": 0.95,
      "language": "en",
      "word_count": 234
    }
  ]
}
```

#### GET /api/sources
List all sources (videos/streams).

**Response:**
```json
{
  "sources": [
    {
      "id": 1,
      "type": "video",
      "filename": "2025-08-22_14-30-45.mp4",
      "start_timestamp": "2025-08-22T14:30:45Z",
      "end_timestamp": "2025-08-22T14:45:30Z",
      "duration_seconds": 885,
      "frame_count": 177
    }
  ]
}
```

### Processing Endpoints (Future)

#### POST /api/analyze/frame/{id}
Trigger vision model analysis on a stored frame.

#### POST /api/analyze/transcript/{id}
Trigger text analysis on a stored transcription.

## Implementation Status

⚠️ **Not yet implemented** - These are planned endpoints for the REST API.

Current implementation is CLI-only. Use the `mem` command-line tool to interact with the database.