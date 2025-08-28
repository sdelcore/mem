# API Documentation

## Overview

The Mem API provides REST endpoints for video processing, frame extraction, transcription, and data retrieval. The API is built with FastAPI and provides automatic interactive documentation.

## Base URL

```
http://localhost:8000
```

## Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Authentication

Currently, no authentication is required. All endpoints are open.

## Endpoints

### 1. Video Capture

#### POST /api/capture
Process a video file for frame and transcript extraction.

**Request Body:**
```json
{
  "filepath": "/path/to/2024-01-01_12-00-00.mp4",
  "config": {
    "frame_interval": 5,
    "chunk_duration": 300
  }
}
```

**Response:**
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "processing",
  "message": "Processing video: 2024-01-01_12-00-00.mp4"
}
```

**Status Codes:**
- 200: Success - job started
- 400: Bad Request - invalid filename format
- 404: Not Found - file doesn't exist
- 500: Internal Server Error

### 2. Universal Search

#### GET /api/search
Universal endpoint for all data retrieval. The behavior depends on the `type` parameter.

**Common Parameters:**
- `type` (required): One of `timeline`, `frame`, `transcript`, `all`
- `limit` (optional, default: 100): Maximum results to return
- `offset` (optional, default: 0): Pagination offset
- `source_id` (optional): Filter by source ID

#### Timeline Search (type=timeline)

Get frames and transcripts within a time range.

**Parameters:**
- `start` (optional): Start time in ISO 8601 format (defaults to 24 hours ago)
- `end` (optional): End time in ISO 8601 format (defaults to now)

**Example:**
```
GET /api/search?type=timeline&start=2024-01-01T00:00:00Z&end=2024-01-02T00:00:00Z
```

**Response:**
```json
{
  "type": "timeline",
  "count": 720,
  "entries": [
    {
      "timestamp": "2024-01-01T00:00:05Z",
      "source_id": 1,
      "scene_changed": false,
      "frame": {
        "frame_id": 123,
        "timestamp": "2024-01-01T00:00:05Z",
        "source_id": 1,
        "perceptual_hash": "abc123...",
        "similarity_score": 99.5,
        "url": "/api/search?type=frame&frame_id=123",
        "metadata": {
          "width": 1920,
          "height": 1080,
          "jpeg_quality": 85
        }
      },
      "transcript": {
        "transcription_id": 456,
        "timestamp": "2024-01-01T00:00:05Z",
        "source_id": 1,
        "text": "Hello, this is the transcribed text...",
        "confidence": 0.95,
        "language": "en",
        "start_timestamp": "2024-01-01T00:00:00Z",
        "end_timestamp": "2024-01-01T00:05:00Z"
      },
      "annotations": [
        {
          "annotation_id": 10,
          "annotation_type": "user_note",
          "content": "Important discussion point",
          "metadata": {"tags": ["meeting", "important"]},
          "created_by": "user123",
          "created_at": "2024-01-01T13:00:00Z"
        },
        {
          "annotation_id": 11,
          "annotation_type": "ai_summary",
          "content": "Presenter discussing quarterly results",
          "metadata": {"model": "gpt-4", "confidence": 0.92},
          "created_by": "system",
          "created_at": "2024-01-01T14:00:00Z"
        }
      ]
    }
  ],
  "pagination": {
    "limit": 100,
    "offset": 0,
    "has_more": true
  }
}
```

#### Frame Retrieval (type=frame)

Get a specific frame as an image.

**Parameters:**
- `frame_id` (required): Frame ID to retrieve
- `format` (optional, default: "jpeg"): Output format ("jpeg" or "png")
- `size` (optional): Size specification ("thumb", "640x480", etc.)

**Example:**
```
GET /api/search?type=frame&frame_id=123&size=thumb
```

**Response:**
- Content-Type: image/jpeg or image/png
- Binary image data

#### Transcript Search (type=transcript)

Search transcripts by text content.

**Parameters:**
- `q` (required): Search query text

**Example:**
```
GET /api/search?type=transcript&q=meeting
```

**Response:**
```json
{
  "type": "transcript",
  "count": 15,
  "results": [
    {
      "transcription_id": 789,
      "source_id": 1,
      "timestamp": "2024-01-01T14:30:00Z",
      "start_timestamp": "2024-01-01T14:30:00Z",
      "end_timestamp": "2024-01-01T14:35:00Z",
      "text": "...the meeting will start at 3 PM...",
      "confidence": 0.92,
      "language": "en"
    }
  ],
  "pagination": {
    "limit": 100,
    "offset": 0,
    "has_more": false
  }
}
```

#### Combined Search (type=all)

Search both timeline and transcripts simultaneously.

**Parameters:**
- `start` (optional): Start time
- `end` (optional): End time
- `q` (optional): Text search query

**Example:**
```
GET /api/search?type=all&q=important&start=2024-01-01T00:00:00Z
```

### 3. System Status

#### GET /api/status
Get system status and statistics.

**Response:**
```json
{
  "system": {
    "version": "1.0.0",
    "database": "connected",
    "uptime": null
  },
  "jobs": {
    "active": 2,
    "completed": 45,
    "failed": 3,
    "total": 50
  },
  "storage": {
    "unique_frames": 50000,
    "total_references": 2500000,
    "deduplication_rate": 95.0,
    "size_mb": 12500.5
  },
  "sources": {
    "total": 25,
    "total_hours": 125.5
  }
}
```

### 4. Job Management

#### GET /api/jobs/{job_id}
Get status of a specific capture job.

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "filepath": "/path/to/video.mp4",
  "created_at": "2024-01-01T12:00:00Z",
  "completed_at": "2024-01-01T12:05:30Z",
  "result": {
    "status": "success",
    "source_id": 123,
    "frames_extracted": 720,
    "transcriptions_created": 12,
    "duration_seconds": 3600,
    "start_time": "2024-01-01T00:00:00Z",
    "end_time": "2024-01-01T01:00:00Z"
  },
  "error": null
}
```

**Status Values:**
- `queued`: Job is waiting to be processed
- `processing`: Job is currently being processed
- `completed`: Job finished successfully
- `failed`: Job failed with an error

### 5. Annotation Management

#### POST /api/annotations
Create a new annotation for a specific timeframe.

**Request Body:**
```json
{
  "source_id": 1,
  "start_timestamp": "2024-01-01T12:30:00Z",
  "end_timestamp": "2024-01-01T12:35:00Z",
  "annotation_type": "user_note",
  "content": "Important discussion about project timeline",
  "metadata": {
    "tags": ["meeting", "project"],
    "importance": "high"
  },
  "created_by": "user123"
}
```

**Response:**
```json
{
  "annotation_id": 1,
  "source_id": 1,
  "start_timestamp": "2024-01-01T12:30:00Z",
  "end_timestamp": "2024-01-01T12:35:00Z",
  "annotation_type": "user_note",
  "content": "Important discussion about project timeline",
  "metadata": {
    "tags": ["meeting", "project"],
    "importance": "high"
  },
  "created_by": "user123",
  "created_at": "2024-01-01T13:00:00Z",
  "updated_at": "2024-01-01T13:00:00Z"
}
```

**Annotation Types:**
- `user_note`: Manual user annotations
- `ai_summary`: AI-generated summaries
- `ocr_output`: Text extracted from frames
- `llm_query`: Results from LLM analysis
- `scene_description`: Visual scene descriptions
- `action_detected`: Detected actions or events
- `custom`: User-defined types

#### PUT /api/annotations/{annotation_id}
Update an existing annotation.

**Request Body:**
```json
{
  "content": "Updated content",
  "metadata": {
    "tags": ["meeting", "project", "urgent"],
    "importance": "critical"
  },
  "annotation_type": "user_note"
}
```

**Response:** Same as POST response with updated fields.

#### DELETE /api/annotations/{annotation_id}
Delete an annotation.

**Response:**
```json
{
  "message": "Annotation 123 deleted successfully"
}
```

#### GET /api/annotations
Query annotations with filters.

**Query Parameters:**
- `source_id` (optional): Filter by source ID
- `start` (optional): Start timestamp for range filter
- `end` (optional): End timestamp for range filter
- `type` (optional): Filter by annotation type
- `limit` (default: 100): Maximum results to return
- `offset` (default: 0): Pagination offset

**Response:**
```json
{
  "annotations": [
    {
      "annotation_id": 1,
      "source_id": 1,
      "start_timestamp": "2024-01-01T12:30:00Z",
      "end_timestamp": "2024-01-01T12:35:00Z",
      "annotation_type": "user_note",
      "content": "Important discussion",
      "metadata": {"tags": ["meeting"]},
      "created_by": "user123",
      "created_at": "2024-01-01T13:00:00Z",
      "updated_at": "2024-01-01T13:00:00Z"
    }
  ],
  "count": 15,
  "pagination": {
    "limit": 100,
    "offset": 0,
    "has_more": false
  }
}
```

#### POST /api/annotations/batch
Create multiple annotations in a single request (useful for AI/LLM batch processing).

**Request Body:**
```json
{
  "source_id": 1,
  "annotations": [
    {
      "start_timestamp": "2024-01-01T12:00:00Z",
      "end_timestamp": "2024-01-01T12:05:00Z",
      "annotation_type": "ocr_output",
      "content": "Screen text: Dashboard showing sales figures",
      "metadata": {"confidence": 0.95}
    },
    {
      "start_timestamp": "2024-01-01T12:05:00Z",
      "end_timestamp": "2024-01-01T12:10:00Z",
      "annotation_type": "ai_summary",
      "content": "User reviewing financial dashboard and taking notes",
      "metadata": {"model": "gpt-4", "confidence": 0.92}
    }
  ]
}
```

**Response:**
```json
{
  "annotation_ids": [123, 124],
  "count": 2,
  "message": "Created 2 annotations"
}
```

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "error": "Error message",
  "detail": "Detailed error information",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Common Status Codes:**
- 400: Bad Request - Invalid parameters
- 404: Not Found - Resource not found
- 500: Internal Server Error - Server error

## Rate Limiting

Currently, no rate limiting is implemented.

## Pagination

Endpoints that return lists support pagination using:
- `limit`: Maximum number of items to return (default: 100, max: 1000)
- `offset`: Number of items to skip (default: 0)

The response includes pagination metadata:
```json
{
  "pagination": {
    "limit": 100,
    "offset": 0,
    "has_more": true
  }
}
```

## Examples

### Using curl

```bash
# Process a video
curl -X POST http://localhost:8000/api/capture \
  -H "Content-Type: application/json" \
  -d '{"filepath": "/videos/2024-01-01_12-00-00.mp4"}'

# Get timeline for last 24 hours
curl "http://localhost:8000/api/search?type=timeline"

# Search transcripts
curl "http://localhost:8000/api/search?type=transcript&q=meeting"

# Get a frame as thumbnail
curl "http://localhost:8000/api/search?type=frame&frame_id=123&size=thumb" \
  --output thumbnail.jpg

# Check system status
curl http://localhost:8000/api/status
```

### Using Python

```python
import requests

# Process a video
response = requests.post(
    "http://localhost:8000/api/capture",
    json={"filepath": "/videos/2024-01-01_12-00-00.mp4"}
)
job = response.json()
print(f"Job ID: {job['job_id']}")

# Search timeline
response = requests.get(
    "http://localhost:8000/api/search",
    params={
        "type": "timeline",
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-01T01:00:00Z"
    }
)
timeline = response.json()
print(f"Found {timeline['count']} entries")

# Get frame image
response = requests.get(
    "http://localhost:8000/api/search",
    params={"type": "frame", "frame_id": 123}
)
with open("frame.jpg", "wb") as f:
    f.write(response.content)
```

## WebSocket Support (Future)

WebSocket endpoints for real-time updates are planned but not yet implemented:
- Real-time capture progress
- Live transcription streaming
- Frame updates as they're processed