#!/usr/bin/env bash
# First-time setup script for Mem
# Run this once on a fresh install

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "${BLUE}    Mem Setup Script${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}\n"

# Step 1: Check Docker
echo -e "${CYAN}[1/6] Checking Docker installation...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed!${NC}"
    echo -e "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}  Docker found: $(docker --version)${NC}"

# Step 2: Check Docker Compose
echo -e "\n${CYAN}[2/6] Checking Docker Compose...${NC}"
if docker compose version &> /dev/null; then
    echo -e "${GREEN}  Docker Compose v2 found${NC}"
elif docker-compose version &> /dev/null; then
    echo -e "${GREEN}  Docker Compose v1 found${NC}"
else
    echo -e "${RED}Docker Compose is not installed!${NC}"
    echo -e "Please install Docker Compose"
    exit 1
fi

# Step 3: Detect GPU
echo -e "\n${CYAN}[3/6] Detecting GPU support...${NC}"
GPU_AVAILABLE=false
if nvidia-smi &> /dev/null; then
    echo -e "${GREEN}  NVIDIA GPU detected:${NC}"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -1 | while read line; do
        echo -e "    $line"
    done

    # Check nvidia-docker (try CDI syntax first, then legacy --gpus)
    if docker run --rm --device nvidia.com/gpu=all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi &> /dev/null 2>&1; then
        echo -e "${GREEN}  NVIDIA Docker runtime is working (CDI)${NC}"
        GPU_AVAILABLE=true
    elif docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi &> /dev/null 2>&1; then
        echo -e "${GREEN}  NVIDIA Docker runtime is working (legacy)${NC}"
        GPU_AVAILABLE=true
    else
        echo -e "${YELLOW}  Warning: nvidia-docker runtime not configured${NC}"
        echo -e "  See: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
        echo -e "  Will default to CPU mode"
    fi
else
    echo -e "${YELLOW}  No NVIDIA GPU detected - will use CPU mode${NC}"
fi

# Step 4: Create directories
echo -e "\n${CYAN}[4/6] Creating data directories...${NC}"
mkdir -p data/{db,uploads,config,streams}
echo -e "${GREEN}  Created: data/db, data/uploads, data/config, data/streams${NC}"

# Step 5: Create configuration files
echo -e "\n${CYAN}[5/6] Setting up configuration...${NC}"

# Copy config.yaml if not exists
if [[ ! -f data/config/config.yaml ]]; then
    if [[ -f mem/config.yaml ]]; then
        cp mem/config.yaml data/config/config.yaml
        echo -e "${GREEN}  Created: data/config/config.yaml${NC}"
    else
        echo -e "${YELLOW}  Warning: mem/config.yaml not found, skipping${NC}"
    fi
else
    echo -e "${YELLOW}  Skipped: data/config/config.yaml already exists${NC}"
fi

# Create .env if not exists
if [[ ! -f .env ]]; then
    cp .env.example .env

    # Auto-detect and set profile (try CDI syntax first, then legacy --gpus)
    if nvidia-smi &> /dev/null && docker run --rm --device nvidia.com/gpu=all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi &> /dev/null 2>&1; then
        sed -i 's/^COMPOSE_PROFILES=.*/COMPOSE_PROFILES=gpu/' .env
        echo -e "${GREEN}  Created: .env (GPU mode via CDI)${NC}"
    elif nvidia-smi &> /dev/null && docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi &> /dev/null 2>&1; then
        sed -i 's/^COMPOSE_PROFILES=.*/COMPOSE_PROFILES=gpu/' .env
        echo -e "${GREEN}  Created: .env (GPU mode via legacy runtime)${NC}"
    else
        sed -i 's/^COMPOSE_PROFILES=.*/COMPOSE_PROFILES=cpu/' .env
        echo -e "${GREEN}  Created: .env (CPU mode)${NC}"
    fi
else
    echo -e "${YELLOW}  Skipped: .env already exists${NC}"
fi

# Make scripts executable
chmod +x run.sh 2>/dev/null || true
chmod +x setup.sh 2>/dev/null || true
chmod +x scripts/*.sh 2>/dev/null || true
chmod +x deploy/*.sh 2>/dev/null || true

# Step 6: Build images (optional)
echo -e "\n${CYAN}[6/6] Build Docker images?${NC}"
echo -e "This will download dependencies and build all containers."
echo -e "It may take 10-15 minutes on first run."
echo ""
read -p "Build images now? [y/N] " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Get profile from .env (match only the variable line, not comments)
    PROFILE=$(grep '^COMPOSE_PROFILES=' .env 2>/dev/null | cut -d= -f2 | tr -d '\n' || echo "cpu")
    echo -e "${BLUE}Building with $PROFILE profile...${NC}"
    ./run.sh "$PROFILE" build
fi

# Done
echo -e "\n${GREEN}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}    Setup Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════${NC}\n"

PROFILE=$(grep '^COMPOSE_PROFILES=' .env 2>/dev/null | cut -d= -f2 | tr -d '\n' || echo "cpu")
echo -e "${BLUE}Quick Start:${NC}"
echo -e "  ${YELLOW}./run.sh up${NC}          Start all services"
echo -e "  ${YELLOW}./run.sh logs${NC}        View logs"
echo -e "  ${YELLOW}./run.sh down${NC}        Stop services"
echo -e "  ${YELLOW}./run.sh status${NC}      Check health"

echo -e "\n${BLUE}Access Points (after starting):${NC}"
echo -e "  Frontend:   http://localhost"
echo -e "  Backend:    http://localhost:8000"
echo -e "  API Docs:   http://localhost:8000/docs"
echo -e "  RTMP:       rtmp://localhost:1935/live"

echo -e "\n${BLUE}Configuration:${NC}"
echo -e "  Profile:    ${YELLOW}$PROFILE${NC}"
echo -e "  Edit ${YELLOW}.env${NC} to change ports and settings"
echo -e "  Edit ${YELLOW}data/config/config.yaml${NC} for Whisper settings"

echo -e "\n${BLUE}OBS Studio RTMP URL:${NC}"
echo -e "  Server:  rtmp://localhost:1935/live"
echo -e "  Key:     (get from web UI after creating a stream)"
