-- ============================================================================
-- MEM TIME-SERIES DATABASE SCHEMA FOR DUCKDB
-- ============================================================================
-- Core capture system for frames and transcriptions with deduplication
-- ============================================================================

-- Sources: Root entity for all capture sessions
CREATE SEQUENCE IF NOT EXISTS sources_seq START 1;
CREATE TABLE IF NOT EXISTS sources (
    source_id BIGINT PRIMARY KEY DEFAULT nextval('sources_seq'),
    source_type VARCHAR NOT NULL CHECK (source_type IN ('video', 'stream', 'webcam')),
    filename VARCHAR NOT NULL,
    location VARCHAR,  -- 'front_door', 'office', etc.
    device_id VARCHAR,  -- Camera identifier
    start_timestamp TIMESTAMPTZ NOT NULL,  -- Absolute UTC time
    end_timestamp TIMESTAMPTZ,
    metadata JSON,  -- Video metadata (fps, width, height, codec, bitrate, etc.)
    created_at TIMESTAMPTZ DEFAULT current_timestamp
);

-- Frames: Frame storage with optional perceptual hash deduplication
CREATE SEQUENCE IF NOT EXISTS frames_seq START 1;
CREATE TABLE IF NOT EXISTS frames (
    frame_id BIGINT PRIMARY KEY DEFAULT nextval('frames_seq'),
    source_id BIGINT NOT NULL,
    first_seen_timestamp TIMESTAMPTZ NOT NULL,  -- When first captured
    last_seen_timestamp TIMESTAMPTZ NOT NULL,   -- Last time this frame appeared
    perceptual_hash VARCHAR(64) NOT NULL,       -- For similarity detection
    image_data BLOB NOT NULL,                   -- JPEG compressed image
    metadata JSON,  -- Additional metadata (jpeg_quality, processing params, etc.)
    FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

-- Timeline: Maps every timestamp to its data
CREATE SEQUENCE IF NOT EXISTS timeline_seq START 1;
CREATE TABLE IF NOT EXISTS timeline (
    entry_id BIGINT PRIMARY KEY DEFAULT nextval('timeline_seq'),
    source_id BIGINT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    frame_id BIGINT,  -- Current frame at this time
    transcription_id BIGINT,  -- Active transcription segment
    similarity_score DOUBLE,  -- How similar to previous frame (0-100)
    FOREIGN KEY (source_id) REFERENCES sources(source_id),
    FOREIGN KEY (frame_id) REFERENCES frames(frame_id),
    UNIQUE(source_id, timestamp)  -- One entry per source per timestamp
);

-- Transcriptions: Audio-to-text segments with time ranges
CREATE SEQUENCE IF NOT EXISTS transcriptions_seq START 1;
CREATE TABLE IF NOT EXISTS transcriptions (
    transcription_id BIGINT PRIMARY KEY DEFAULT nextval('transcriptions_seq'),
    source_id BIGINT NOT NULL,
    start_timestamp TIMESTAMPTZ NOT NULL,
    end_timestamp TIMESTAMPTZ NOT NULL,
    text TEXT NOT NULL,
    confidence DOUBLE,
    language VARCHAR(10),
    whisper_model VARCHAR DEFAULT 'base',
    has_overlap BOOLEAN DEFAULT FALSE,  -- Whether this chunk has overlap regions
    overlap_start TIMESTAMPTZ,  -- Start of overlap with previous chunk (if any)
    overlap_end TIMESTAMPTZ,    -- End of overlap with next chunk (if any)
    FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Timeline indexes for temporal queries
CREATE INDEX IF NOT EXISTS idx_timeline_temporal ON timeline(timestamp, source_id);
CREATE INDEX IF NOT EXISTS idx_timeline_source ON timeline(source_id, timestamp);
-- Index for finding scene changes based on similarity score
CREATE INDEX IF NOT EXISTS idx_timeline_similarity ON timeline(source_id, similarity_score, timestamp);

-- Frame lookup indexes
CREATE INDEX IF NOT EXISTS idx_frames_hash ON frames(source_id, perceptual_hash);
CREATE INDEX IF NOT EXISTS idx_frames_temporal ON frames(source_id, first_seen_timestamp);

-- Transcription temporal indexes
CREATE INDEX IF NOT EXISTS idx_trans_temporal ON transcriptions(start_timestamp, end_timestamp);
CREATE INDEX IF NOT EXISTS idx_trans_source ON transcriptions(source_id, start_timestamp);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Get current state for active sources
CREATE OR REPLACE VIEW current_state AS
WITH latest_frames AS (
    SELECT DISTINCT ON (source_id) 
        source_id, 
        frame_id, 
        timestamp
    FROM timeline
    WHERE frame_id IS NOT NULL
    ORDER BY source_id, timestamp DESC
),
latest_trans AS (
    SELECT DISTINCT ON (source_id)
        source_id,
        transcription_id,
        text,
        end_timestamp
    FROM transcriptions
    ORDER BY source_id, end_timestamp DESC
)
SELECT 
    s.source_id,
    s.location,
    s.filename,
    lf.timestamp as last_frame_time,
    lt.text as last_transcript,
    lt.end_timestamp as last_trans_time
FROM sources s
LEFT JOIN latest_frames lf ON s.source_id = lf.source_id
LEFT JOIN latest_trans lt ON s.source_id = lt.source_id;

-- Scene changes with timing (scene_changed when similarity < 95)
CREATE OR REPLACE VIEW scene_changes AS
SELECT 
    t.timestamp,
    t.source_id,
    s.location,
    t.similarity_score,
    LAG(t.timestamp) OVER (PARTITION BY t.source_id ORDER BY t.timestamp) as previous_change,
    LEAD(t.timestamp) OVER (PARTITION BY t.source_id ORDER BY t.timestamp) as next_change
FROM timeline t
JOIN sources s ON t.source_id = s.source_id
WHERE t.similarity_score < 95.0;

-- Deduplication statistics per source
CREATE OR REPLACE VIEW deduplication_stats AS
SELECT 
    s.source_id,
    s.filename,
    s.location,
    COUNT(DISTINCT t.frame_id) as unique_frames,
    COUNT(t.entry_id) as total_timeline_entries,
    ROUND((1.0 - COUNT(DISTINCT t.frame_id)::DOUBLE / COUNT(t.entry_id)) * 100, 2) as dedup_percentage,
    SUM(OCTET_LENGTH(f.image_data)) / (1024.0 * 1024.0) as total_size_mb
FROM sources s
JOIN timeline t ON s.source_id = t.source_id
LEFT JOIN frames f ON t.frame_id = f.frame_id
GROUP BY s.source_id, s.filename, s.location;

-- ============================================================================
-- ANNOTATIONS FOR TIMEFRAMES
-- ============================================================================

-- Timeframe annotations: User notes, AI summaries, OCR output, etc.
CREATE SEQUENCE IF NOT EXISTS annotations_seq START 1;
CREATE TABLE IF NOT EXISTS timeframe_annotations (
    annotation_id BIGINT PRIMARY KEY DEFAULT nextval('annotations_seq'),
    source_id BIGINT NOT NULL,
    start_timestamp TIMESTAMPTZ NOT NULL,
    end_timestamp TIMESTAMPTZ NOT NULL,
    annotation_type VARCHAR NOT NULL CHECK (annotation_type IN (
        'user_note', 'ai_summary', 'ocr_output', 'llm_query',
        'scene_description', 'action_detected', 'custom'
    )),
    content TEXT NOT NULL,
    metadata JSON,  -- Additional structured data (confidence, model used, tags, etc.)
    created_by VARCHAR DEFAULT 'system',  -- User ID or 'system'
    created_at TIMESTAMPTZ DEFAULT current_timestamp,
    updated_at TIMESTAMPTZ DEFAULT current_timestamp,
    FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

-- Indexes for efficient annotation queries
CREATE INDEX IF NOT EXISTS idx_annotations_temporal ON timeframe_annotations(start_timestamp, end_timestamp);
CREATE INDEX IF NOT EXISTS idx_annotations_source ON timeframe_annotations(source_id, start_timestamp);
CREATE INDEX IF NOT EXISTS idx_annotations_type ON timeframe_annotations(annotation_type, source_id);
CREATE INDEX IF NOT EXISTS idx_annotations_created ON timeframe_annotations(created_at DESC);

-- ============================================================================
-- COMPUTED VIEWS FOR BACKWARD COMPATIBILITY
-- ============================================================================

-- Sources with computed duration
CREATE OR REPLACE VIEW sources_with_computed AS
SELECT 
    s.*,
    EXTRACT(EPOCH FROM (s.end_timestamp - s.start_timestamp)) as duration_seconds,
    s.metadata->>'$.fps' as fps,
    s.metadata->>'$.width' as width,
    s.metadata->>'$.height' as height
FROM sources s;

-- Frames with computed fields
CREATE OR REPLACE VIEW frames_with_computed AS
SELECT 
    f.*,
    OCTET_LENGTH(f.image_data) as size_bytes,
    (SELECT COUNT(*) FROM timeline t WHERE t.frame_id = f.frame_id) as reference_count,
    s.metadata->>'$.width' as width,
    s.metadata->>'$.height' as height,
    f.metadata->>'$.jpeg_quality' as jpeg_quality
FROM frames f
JOIN sources s ON f.source_id = s.source_id;

-- Transcriptions with word count
CREATE OR REPLACE VIEW transcriptions_with_computed AS
SELECT 
    t.*,
    array_length(string_split(t.text, ' '), 1) as word_count
FROM transcriptions t;

-- Timeline with scene_changed flag
CREATE OR REPLACE VIEW timeline_with_computed AS
SELECT 
    t.*,
    CASE WHEN t.similarity_score < 95.0 THEN TRUE ELSE FALSE END as scene_changed
FROM timeline t;