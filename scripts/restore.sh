#!/usr/bin/env bash
# Restore script for Mem data
# Restores from a backup tarball created by backup.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Configuration
DATA_DIR="${DATA_DIR:-$PROJECT_DIR/data}"

# Parse arguments
BACKUP_FILE=""
FORCE=false
SKIP_STOP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --force|-f)
            FORCE=true
            shift
            ;;
        --skip-stop)
            SKIP_STOP=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 <backup-file> [options]"
            echo ""
            echo "Arguments:"
            echo "  backup-file   Path to backup tarball (*.tar.gz)"
            echo ""
            echo "Options:"
            echo "  --force, -f   Skip confirmation prompts"
            echo "  --skip-stop   Don't stop services before restore"
            echo "  --help        Show this help message"
            exit 0
            ;;
        *)
            if [[ -z "$BACKUP_FILE" ]]; then
                BACKUP_FILE="$1"
            else
                echo -e "${RED}Unknown argument: $1${NC}"
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate backup file
if [[ -z "$BACKUP_FILE" ]]; then
    echo -e "${RED}Error: No backup file specified${NC}"
    echo "Usage: $0 <backup-file>"
    exit 1
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo -e "${RED}Error: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "${BLUE}    Mem Restore Script${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}\n"

echo -e "${YELLOW}Backup file: $BACKUP_FILE${NC}"
echo -e "${YELLOW}Data directory: $DATA_DIR${NC}\n"

# Warning
if [[ "$FORCE" != "true" ]]; then
    echo -e "${RED}WARNING: This will overwrite existing data!${NC}"
    read -p "Are you sure you want to continue? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Restore cancelled."
        exit 0
    fi
fi

# Stop services
if [[ "$SKIP_STOP" != "true" ]]; then
    echo -e "\n${CYAN}[1/5] Stopping services...${NC}"
    if docker compose ps 2>/dev/null | grep -q "mem"; then
        ./run.sh down 2>/dev/null || docker compose down 2>/dev/null || true
        echo -e "${GREEN}  Services stopped${NC}"
    else
        echo -e "${YELLOW}  No running services found${NC}"
    fi
else
    echo -e "\n${CYAN}[1/5] Skipping service stop (--skip-stop)${NC}"
fi

# Create temporary directory for extraction
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Extract backup
echo -e "\n${CYAN}[2/5] Extracting backup...${NC}"
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"

# Check backup contents
if [[ ! -d "$TEMP_DIR/backup" ]]; then
    echo -e "${RED}Error: Invalid backup format - missing 'backup' directory${NC}"
    exit 1
fi

# Show backup info if available
if [[ -f "$TEMP_DIR/backup/backup-info.json" ]]; then
    echo -e "  Backup info:"
    cat "$TEMP_DIR/backup/backup-info.json" | while read line; do
        echo -e "    $line"
    done
fi

# Create data directory if needed
mkdir -p "$DATA_DIR"

# Backup current data (just in case)
echo -e "\n${CYAN}[3/5] Backing up current data...${NC}"
CURRENT_BACKUP="$DATA_DIR/../data-pre-restore-$(date +%Y%m%d_%H%M%S)"
if [[ -d "$DATA_DIR" ]] && [[ "$(ls -A "$DATA_DIR" 2>/dev/null)" ]]; then
    mv "$DATA_DIR" "$CURRENT_BACKUP"
    mkdir -p "$DATA_DIR"
    echo -e "${GREEN}  Current data moved to: $CURRENT_BACKUP${NC}"
else
    echo -e "${YELLOW}  No existing data to backup${NC}"
fi

# Restore database
echo -e "\n${CYAN}[4/5] Restoring database...${NC}"
if [[ -d "$TEMP_DIR/backup/db/parquet" ]]; then
    # Restore from Parquet format
    echo -e "  Detected Parquet format backup"
    mkdir -p "$DATA_DIR/db"

    if command -v duckdb &> /dev/null; then
        # Import from Parquet files
        duckdb "$DATA_DIR/db/mem.duckdb" <<EOF
-- Create tables and import from Parquet
CREATE TABLE sources AS SELECT * FROM read_parquet('$TEMP_DIR/backup/db/parquet/sources.parquet');
CREATE TABLE unique_frames AS SELECT * FROM read_parquet('$TEMP_DIR/backup/db/parquet/unique_frames.parquet');
CREATE TABLE timeline AS SELECT * FROM read_parquet('$TEMP_DIR/backup/db/parquet/timeline.parquet');
CREATE TABLE transcriptions AS SELECT * FROM read_parquet('$TEMP_DIR/backup/db/parquet/transcriptions.parquet');
CREATE TABLE timeframe_annotations AS SELECT * FROM read_parquet('$TEMP_DIR/backup/db/parquet/timeframe_annotations.parquet');
CREATE TABLE streams AS SELECT * FROM read_parquet('$TEMP_DIR/backup/db/parquet/streams.parquet');
CREATE TABLE speaker_profiles AS SELECT * FROM read_parquet('$TEMP_DIR/backup/db/parquet/speaker_profiles.parquet');
EOF
        echo -e "${GREEN}  Imported from Parquet format${NC}"
    else
        echo -e "${RED}Error: duckdb CLI required for Parquet restore${NC}"
        echo -e "Install with: pip install duckdb-cli or download from https://duckdb.org/docs/installation/"
        exit 1
    fi
elif [[ -d "$TEMP_DIR/backup/db" ]]; then
    # Direct copy of DuckDB file
    cp -r "$TEMP_DIR/backup/db" "$DATA_DIR/"
    echo -e "${GREEN}  Restored database file${NC}"
else
    echo -e "${YELLOW}  No database in backup${NC}"
    mkdir -p "$DATA_DIR/db"
fi

# Restore uploads
echo -e "\n${CYAN}[5/5] Restoring uploads and config...${NC}"
if [[ -d "$TEMP_DIR/backup/uploads" ]]; then
    cp -r "$TEMP_DIR/backup/uploads" "$DATA_DIR/"
    UPLOAD_COUNT=$(find "$DATA_DIR/uploads" -type f 2>/dev/null | wc -l)
    echo -e "${GREEN}  Restored $UPLOAD_COUNT upload files${NC}"
else
    mkdir -p "$DATA_DIR/uploads"
    echo -e "${YELLOW}  No uploads in backup${NC}"
fi

# Restore config
if [[ -d "$TEMP_DIR/backup/config" ]]; then
    cp -r "$TEMP_DIR/backup/config" "$DATA_DIR/"
    echo -e "${GREEN}  Restored configuration${NC}"
else
    mkdir -p "$DATA_DIR/config"
    echo -e "${YELLOW}  No config in backup${NC}"
fi

# Restore .env if present
if [[ -f "$TEMP_DIR/backup/.env" ]]; then
    if [[ -f "$PROJECT_DIR/.env" ]] && [[ "$FORCE" != "true" ]]; then
        echo -e "${YELLOW}  .env already exists, saved backup to .env.restored${NC}"
        cp "$TEMP_DIR/backup/.env" "$PROJECT_DIR/.env.restored"
    else
        cp "$TEMP_DIR/backup/.env" "$PROJECT_DIR/.env"
        echo -e "${GREEN}  Restored .env file${NC}"
    fi
fi

# Ensure proper permissions
chmod -R 755 "$DATA_DIR"

echo -e "\n${GREEN}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}    Restore Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════${NC}\n"

echo -e "${BLUE}Next steps:${NC}"
echo -e "  1. Start services: ${YELLOW}./run.sh up${NC}"
echo -e "  2. Verify data: ${YELLOW}curl http://localhost:8000/api/status${NC}"

if [[ -d "$CURRENT_BACKUP" ]]; then
    echo -e "\n${YELLOW}Previous data backed up to:${NC}"
    echo -e "  $CURRENT_BACKUP"
    echo -e "  Delete when confirmed working: rm -rf \"$CURRENT_BACKUP\""
fi
