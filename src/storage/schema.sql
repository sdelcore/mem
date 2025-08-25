-- Mem Database Schema
-- Core tables for capturing video frames and transcriptions with absolute UTC timestamps

-- Sources table: tracks all video/stream sources
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK(type IN ('video', 'stream', 'upload')),
    filename TEXT NOT NULL,
    start_timestamp TIMESTAMP NOT NULL,  -- Absolute UTC time when recording started
    end_timestamp TIMESTAMP,             -- Absolute UTC time when recording ended
    duration_seconds REAL,               -- Duration in seconds
    frame_count INTEGER DEFAULT 0,       -- Number of frames extracted
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON                        -- Additional metadata (resolution, fps, etc.)
);

-- Frames table: stores extracted video frames as BLOBs
CREATE TABLE IF NOT EXISTS frames (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL,        -- Absolute UTC timestamp of frame
    image_data BLOB NOT NULL,           -- Full image stored as BLOB (JPEG)
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    format TEXT DEFAULT 'jpeg',
    size_bytes INTEGER,                  -- Size of image_data in bytes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
);

-- Transcriptions table: stores audio transcriptions with time ranges
CREATE TABLE IF NOT EXISTS transcriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    start_timestamp TIMESTAMP NOT NULL,  -- Absolute UTC start time
    end_timestamp TIMESTAMP NOT NULL,    -- Absolute UTC end time
    text TEXT NOT NULL,
    confidence REAL,                     -- Confidence score from Whisper
    language TEXT,                       -- Detected language
    word_count INTEGER,                  -- Number of words in transcript
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
);

-- Frame analysis table: stores post-processing results for frames
CREATE TABLE IF NOT EXISTS frame_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    frame_id INTEGER NOT NULL,
    model_name TEXT NOT NULL,            -- Model used for analysis
    analysis_type TEXT NOT NULL,         -- 'ocr', 'object_detection', 'scene', etc.
    result JSON NOT NULL,                -- Analysis results as JSON
    processing_time_ms INTEGER,          -- Time taken to process in milliseconds
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (frame_id) REFERENCES frames(id) ON DELETE CASCADE
);

-- Transcript analysis table: stores post-processing results for transcripts
CREATE TABLE IF NOT EXISTS transcript_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transcription_id INTEGER NOT NULL,
    model_name TEXT NOT NULL,            -- Model used for analysis
    analysis_type TEXT NOT NULL,         -- 'summary', 'classification', 'entities', etc.
    result JSON NOT NULL,                -- Analysis results as JSON
    processing_time_ms INTEGER,          -- Time taken to process in milliseconds
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transcription_id) REFERENCES transcriptions(id) ON DELETE CASCADE
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_frames_timestamp ON frames(timestamp);
CREATE INDEX IF NOT EXISTS idx_frames_source ON frames(source_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_transcriptions_timestamp ON transcriptions(start_timestamp, end_timestamp);
CREATE INDEX IF NOT EXISTS idx_transcriptions_source ON transcriptions(source_id, start_timestamp);
CREATE INDEX IF NOT EXISTS idx_sources_timestamp ON sources(start_timestamp, end_timestamp);
CREATE INDEX IF NOT EXISTS idx_frame_analysis_frame ON frame_analysis(frame_id);
CREATE INDEX IF NOT EXISTS idx_transcript_analysis_trans ON transcript_analysis(transcription_id);