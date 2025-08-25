#!/bin/bash

# Test script for Mem video processing pipeline
# This script:
# 1. Creates a test video if needed
# 2. Processes it with mem capture
# 3. Displays the transcriptions
# 4. Exports and displays a frame

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Mem Pipeline Test Script ===${NC}"
echo

# Configuration
TEST_DB="test_mem.db"
TEST_VIDEO_DIR="data/test_videos"
EXPORT_DIR="data/test_exports"

# Function to print status
print_status() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Clean up function
cleanup() {
    print_status "Cleaning up test files..."
    rm -f "$TEST_DB"
    rm -rf "$EXPORT_DIR"
    print_success "Cleanup complete"
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Step 1: Create test database
print_status "Creating fresh test database..."
rm -f "$TEST_DB"
uv run mem reset-db --confirm --db "$TEST_DB"
# Ensure database is writable
chmod 644 "$TEST_DB" 2>/dev/null || true
print_success "Database created: $TEST_DB"
echo

# Step 2: Find test video from ~/Videos/
print_status "Looking for test video..."
mkdir -p "$EXPORT_DIR"

# First check ~/Videos/ for any video with correct format
TEST_VIDEO=$(find ~/Videos/ -name "????-??-??_??-??-??.mkv" -type f 2>/dev/null | head -n 1)

if [ -z "$TEST_VIDEO" ]; then
    # If no correctly formatted video, try to find any .mp4 in ~/Videos/
    print_status "No video with correct format found. Looking for any .mp4 file in ~/Videos/..."
    ANY_VIDEO=$(find ~/Videos/ -name "*.mp4" -type f 2>/dev/null | head -n 1)
    
    if [ -n "$ANY_VIDEO" ]; then
        print_error "Found video: $ANY_VIDEO"
        print_error "But it doesn't match required format: YYYY-MM-DD_HH-MM-SS.mp4"
        print_status "You need to rename it to match the format."
        echo
        echo "Example rename command:"
        SUGGESTED_NAME="$(date +%Y-%m-%d_%H-%M-%S).mp4"
        echo "  mv \"$ANY_VIDEO\" \"~/Videos/$SUGGESTED_NAME\""
        exit 1
    else
        print_error "No video files found in ~/Videos/"
        print_status "Creating a test video instead..."
        mkdir -p "$TEST_VIDEO_DIR"
        TEST_VIDEO=$(uv run python scripts/create_test_video.py | grep "Created test video:" | cut -d: -f2 | xargs)
        if [ -z "$TEST_VIDEO" ]; then
            print_error "Failed to create test video"
            exit 1
        fi
    fi
fi

print_success "Using test video: $TEST_VIDEO"
echo

# Step 3: Process the video
print_status "Processing video with mem capture..."
echo "Options:"
echo "  - Frame interval: 2 seconds"
echo "  - JPEG quality: 90"
echo "  - Audio chunks: 30 seconds"
echo "  - Whisper model: tiny (faster for testing)"
echo

OUTPUT=$(uv run mem capture "$TEST_VIDEO" \
    --frame-interval 2 \
    --quality 90 \
    --chunk-duration 30 \
    --whisper-model tiny \
    --db "$TEST_DB" 2>&1)

# Extract source ID from output
SOURCE_ID=$(echo "$OUTPUT" | grep "Source ID:" | grep -oE '[0-9]+' | head -n 1)

if [ -z "$SOURCE_ID" ]; then
    print_error "Failed to process video. Output:"
    echo "$OUTPUT"
    exit 1
fi

print_success "Video processed successfully! Source ID: $SOURCE_ID"
echo

# Step 4: Check database statistics
print_status "Checking database statistics..."
STATS=$(uv run mem stats --db "$TEST_DB")
echo "$STATS"
echo

# Step 5: List frames
print_status "Listing captured frames..."
# Use a wide time range to ensure we get the frames
FRAMES=$(uv run mem list-frames --start "2020-01-01T00:00:00" --end "2030-12-31T23:59:59" --source-id "$SOURCE_ID" --db "$TEST_DB")
echo "$FRAMES"
echo

# Extract last frame ID (get the last row with a frame ID)
FRAME_ID=$(uv run mem list-frames --start "2020-01-01T00:00:00" --end "2030-12-31T23:59:59" --source-id "$SOURCE_ID" --db "$TEST_DB" 2>/dev/null | grep -E '│\s+[0-9]+\s+│' | tail -n 1 | awk -F'│' '{print $2}' | xargs)

if [ -z "$FRAME_ID" ]; then
    print_error "No frames found in database"
    exit 1
fi

print_success "Found last frame ID: $FRAME_ID"
echo

# Step 6: List transcriptions and show the last one
print_status "Checking for transcriptions..."
# Use a wide time range to ensure we get all transcriptions
TRANSCRIPTS=$(uv run mem list-transcripts --start "2020-01-01T00:00:00" --end "2030-12-31T23:59:59" --source-id "$SOURCE_ID" --db "$TEST_DB" 2>/dev/null)

if echo "$TRANSCRIPTS" | grep -q "No transcriptions found"; then
    print_status "No transcriptions found (video might not have audio)"
else
    # Count total transcriptions
    TRANSCRIPT_COUNT=$(echo "$TRANSCRIPTS" | grep -c "^ID [0-9]")
    print_success "Found $TRANSCRIPT_COUNT transcriptions"
    
    # Extract and display the last transcription entry (includes ID line + next 4 lines for full entry)
    echo
    echo "Last transcription:"
    echo "$TRANSCRIPTS" | grep -A 4 "^ID [0-9]" | tail -n 5
    echo
fi
echo

# Step 7: Export a frame
print_status "Exporting frame $FRAME_ID..."
EXPORT_FILE="$EXPORT_DIR/frame_${FRAME_ID}.jpg"
uv run mem export-frame --frame-id "$FRAME_ID" --output "$EXPORT_FILE" --db "$TEST_DB"
print_success "Frame exported to: $EXPORT_FILE"
echo

# Step 8: Display frame (if possible)
print_status "Checking exported frame..."
if [ -f "$EXPORT_FILE" ]; then
    # Get file info
    FILE_SIZE=$(ls -lh "$EXPORT_FILE" | awk '{print $5}')
    
    # Try to get image dimensions using Python PIL
    DIMENSIONS=$(uv run python -c "
from PIL import Image
img = Image.open('$EXPORT_FILE')
print(f'{img.width}x{img.height}')
" 2>/dev/null || echo "unknown")
    
    print_success "Frame details:"
    echo "  File: $EXPORT_FILE"
    echo "  Size: $FILE_SIZE"
    echo "  Dimensions: $DIMENSIONS"
    
    # Try to display the image if we have a display
    if command -v xdg-open &> /dev/null; then
        print_status "Opening image with default viewer..."
        xdg-open "$EXPORT_FILE" 2>/dev/null &
    elif command -v open &> /dev/null; then
        print_status "Opening image with default viewer..."
        open "$EXPORT_FILE" 2>/dev/null &
    else
        print_status "No image viewer available. Image saved at: $EXPORT_FILE"
    fi
else
    print_error "Failed to export frame"
    exit 1
fi

echo
echo -e "${GREEN}=== Test Complete ===${NC}"
echo
print_success "All tests passed successfully!"
echo
echo "Summary:"
echo "  - Database: $TEST_DB"
echo "  - Video processed: $TEST_VIDEO"
echo "  - Source ID: $SOURCE_ID"
echo "  - Frame exported: $EXPORT_FILE"
echo
echo "You can explore the test database with:"
echo "  uv run mem stats --db $TEST_DB"
echo "  uv run mem list-frames --db $TEST_DB"
echo "  uv run mem list-transcripts --db $TEST_DB"
echo
echo "Note: Test database will be cleaned up on exit."
echo "Press Ctrl+C to exit and clean up test files."

# Wait for user to see the image
read -p "Press Enter to finish and clean up..."
