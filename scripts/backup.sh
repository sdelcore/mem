#!/usr/bin/env bash
# Backup script for Mem data
# Creates a tarball of database, uploads, and config

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Configuration
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
DATA_DIR="${DATA_DIR:-$PROJECT_DIR/data}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="mem-backup-${TIMESTAMP}"
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"

# Parse arguments
EXPORT_PARQUET=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --parquet)
            EXPORT_PARQUET=true
            shift
            ;;
        --output)
            BACKUP_FILE="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --parquet     Export DuckDB to Parquet format (portable)"
            echo "  --output FILE Output file path (default: backups/mem-backup-TIMESTAMP.tar.gz)"
            echo "  --help        Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "${BLUE}    Mem Backup Script${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}\n"

# Check if data directory exists
if [[ ! -d "$DATA_DIR" ]]; then
    echo -e "${RED}Error: Data directory not found: $DATA_DIR${NC}"
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create temporary directory for backup staging
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

echo -e "${CYAN}[1/4] Preparing backup...${NC}"
mkdir -p "$TEMP_DIR/backup"

# Check if services are running and warn
if docker compose ps 2>/dev/null | grep -q "mem-backend"; then
    echo -e "${YELLOW}Warning: Services appear to be running.${NC}"
    echo -e "${YELLOW}For a consistent backup, consider stopping services first: ./run.sh down${NC}"
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Backup database
echo -e "\n${CYAN}[2/4] Backing up database...${NC}"
if [[ -f "$DATA_DIR/db/mem.duckdb" ]]; then
    if [[ "$EXPORT_PARQUET" == "true" ]]; then
        echo -e "  Exporting to Parquet format..."

        # Use DuckDB CLI to export tables to Parquet
        if command -v duckdb &> /dev/null; then
            mkdir -p "$TEMP_DIR/backup/db/parquet"

            # Export each table
            duckdb "$DATA_DIR/db/mem.duckdb" <<EOF
COPY (SELECT * FROM sources) TO '$TEMP_DIR/backup/db/parquet/sources.parquet' (FORMAT PARQUET);
COPY (SELECT * FROM unique_frames) TO '$TEMP_DIR/backup/db/parquet/unique_frames.parquet' (FORMAT PARQUET);
COPY (SELECT * FROM timeline) TO '$TEMP_DIR/backup/db/parquet/timeline.parquet' (FORMAT PARQUET);
COPY (SELECT * FROM transcriptions) TO '$TEMP_DIR/backup/db/parquet/transcriptions.parquet' (FORMAT PARQUET);
COPY (SELECT * FROM timeframe_annotations) TO '$TEMP_DIR/backup/db/parquet/timeframe_annotations.parquet' (FORMAT PARQUET);
COPY (SELECT * FROM streams) TO '$TEMP_DIR/backup/db/parquet/streams.parquet' (FORMAT PARQUET);
COPY (SELECT * FROM speaker_profiles) TO '$TEMP_DIR/backup/db/parquet/speaker_profiles.parquet' (FORMAT PARQUET);
EOF
            echo -e "${GREEN}  Exported tables to Parquet format${NC}"
        else
            echo -e "${YELLOW}  Warning: duckdb CLI not found, falling back to direct copy${NC}"
            cp -r "$DATA_DIR/db" "$TEMP_DIR/backup/"
        fi
    else
        # Direct copy of DuckDB file
        cp -r "$DATA_DIR/db" "$TEMP_DIR/backup/"
        echo -e "${GREEN}  Copied database file${NC}"
    fi
else
    echo -e "${YELLOW}  No database found, skipping${NC}"
fi

# Backup uploads
echo -e "\n${CYAN}[3/4] Backing up uploads...${NC}"
if [[ -d "$DATA_DIR/uploads" ]] && [[ "$(ls -A "$DATA_DIR/uploads" 2>/dev/null)" ]]; then
    cp -r "$DATA_DIR/uploads" "$TEMP_DIR/backup/"
    UPLOAD_COUNT=$(find "$DATA_DIR/uploads" -type f | wc -l)
    echo -e "${GREEN}  Copied $UPLOAD_COUNT files${NC}"
else
    mkdir -p "$TEMP_DIR/backup/uploads"
    echo -e "${YELLOW}  No uploads found, creating empty directory${NC}"
fi

# Backup config
echo -e "\n${CYAN}[4/4] Backing up configuration...${NC}"
if [[ -d "$DATA_DIR/config" ]]; then
    cp -r "$DATA_DIR/config" "$TEMP_DIR/backup/"
    echo -e "${GREEN}  Copied configuration files${NC}"
else
    mkdir -p "$TEMP_DIR/backup/config"
    echo -e "${YELLOW}  No config found, creating empty directory${NC}"
fi

# Also backup .env if it exists
if [[ -f "$PROJECT_DIR/.env" ]]; then
    cp "$PROJECT_DIR/.env" "$TEMP_DIR/backup/"
    echo -e "${GREEN}  Copied .env file${NC}"
fi

# Create metadata file
cat > "$TEMP_DIR/backup/backup-info.json" <<EOF
{
    "timestamp": "$(date -Iseconds)",
    "hostname": "$(hostname)",
    "format": "$([ "$EXPORT_PARQUET" == "true" ] && echo "parquet" || echo "duckdb")",
    "version": "1.0"
}
EOF

# Create tarball
echo -e "\n${BLUE}Creating archive...${NC}"
tar -czf "$BACKUP_FILE" -C "$TEMP_DIR" backup

# Calculate size
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)

echo -e "\n${GREEN}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}    Backup Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════${NC}\n"

echo -e "${YELLOW}Backup Details:${NC}"
echo -e "  File: $BACKUP_FILE"
echo -e "  Size: $BACKUP_SIZE"
echo -e "  Format: $([ "$EXPORT_PARQUET" == "true" ] && echo "Parquet (portable)" || echo "DuckDB (native)")"

echo -e "\n${BLUE}To restore:${NC}"
echo -e "  ./scripts/restore.sh $BACKUP_FILE"
