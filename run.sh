#!/usr/bin/env bash
# Simple run script for Mem deployment
# Usage: ./run.sh [gpu|cpu] [command]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env if exists
if [[ -f .env ]]; then
    set -a
    source .env
    set +a
fi

# Default profile from .env or 'gpu'
DEFAULT_PROFILE="${COMPOSE_PROFILES:-gpu}"
PROFILE="${1:-$DEFAULT_PROFILE}"
COMMAND="${2:-up}"

# If first arg looks like a command, shift it
if [[ "$PROFILE" =~ ^(up|down|restart|logs|status|build|pull|shell|help)$ ]]; then
    COMMAND="$PROFILE"
    PROFILE="$DEFAULT_PROFILE"
fi

# Validate profile
if [[ "$PROFILE" != "gpu" && "$PROFILE" != "cpu" ]]; then
    echo -e "${RED}Error: Invalid profile '$PROFILE'. Use 'gpu' or 'cpu'${NC}"
    exit 1
fi

# Help
show_help() {
    echo -e "${BLUE}Mem Docker Runner${NC}"
    echo ""
    echo "Usage: ./run.sh [profile] [command]"
    echo ""
    echo "Profiles:"
    echo "  gpu     Run with NVIDIA GPU support (default if GPU detected)"
    echo "  cpu     Run with CPU-only backend"
    echo ""
    echo "Commands:"
    echo "  up      Start all services (default)"
    echo "  down    Stop all services"
    echo "  restart Restart all services"
    echo "  logs    View logs (follow mode)"
    echo "  status  Show service status"
    echo "  build   Build images"
    echo "  pull    Pull latest images"
    echo "  shell   Open shell in backend container"
    echo "  help    Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./run.sh              # Start with default profile"
    echo "  ./run.sh gpu up       # Start with GPU support"
    echo "  ./run.sh cpu up       # Start CPU-only"
    echo "  ./run.sh logs         # View logs (uses default profile)"
    echo "  ./run.sh gpu down     # Stop services"
    echo ""
    echo "Configuration:"
    echo "  Edit .env to change default profile and ports"
    echo "  Edit data/config/config.yaml for Whisper settings"
}

# Check prerequisites
check_prereqs() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        exit 1
    fi

    if ! docker compose version &> /dev/null && ! docker-compose version &> /dev/null; then
        echo -e "${RED}Error: Docker Compose is not installed${NC}"
        exit 1
    fi

    if [[ "$PROFILE" == "gpu" ]]; then
        if ! nvidia-smi &> /dev/null; then
            echo -e "${YELLOW}Warning: NVIDIA GPU not detected. Consider using 'cpu' profile.${NC}"
            echo -e "${YELLOW}You can switch profiles with: ./run.sh cpu up${NC}"
            read -p "Continue with GPU profile anyway? [y/N] " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    fi
}

# Docker compose command (handle both v1 and v2)
dc() {
    if docker compose version &> /dev/null; then
        docker compose --profile "$PROFILE" "$@"
    else
        docker-compose --profile "$PROFILE" "$@"
    fi
}

# Create data directories
setup_dirs() {
    mkdir -p data/{db,uploads,config,streams}

    # Copy default config if not exists
    if [[ ! -f data/config/config.yaml ]]; then
        if [[ -f mem/config.yaml ]]; then
            cp mem/config.yaml data/config/config.yaml
            echo -e "${GREEN}Created default config at data/config/config.yaml${NC}"
        fi
    fi
}

# Main command handler
case "$COMMAND" in
    up)
        check_prereqs
        setup_dirs
        echo -e "${BLUE}Starting Mem with ${PROFILE} profile...${NC}"
        dc up -d
        echo ""
        echo -e "${GREEN}Services started!${NC}"
        echo ""
        echo -e "${YELLOW}Access Points:${NC}"
        echo -e "  Frontend:  http://localhost:${FRONTEND_PORT:-80}"
        echo -e "  Backend:   http://localhost:${BACKEND_PORT:-8000}"
        echo -e "  API Docs:  http://localhost:${BACKEND_PORT:-8000}/docs"
        echo -e "  RTMP:      rtmp://localhost:${RTMP_PORT:-1935}/live"
        echo ""
        echo -e "${YELLOW}Commands:${NC}"
        echo -e "  ./run.sh logs     View logs"
        echo -e "  ./run.sh status   Check status"
        echo -e "  ./run.sh down     Stop services"
        ;;
    down)
        echo -e "${BLUE}Stopping Mem services...${NC}"
        dc down
        echo -e "${GREEN}Services stopped${NC}"
        ;;
    restart)
        echo -e "${BLUE}Restarting Mem services...${NC}"
        dc restart
        echo -e "${GREEN}Services restarted${NC}"
        ;;
    logs)
        dc logs -f
        ;;
    status)
        echo -e "${BLUE}Service Status (${PROFILE} profile):${NC}"
        dc ps
        ;;
    build)
        echo -e "${BLUE}Building images for ${PROFILE} profile...${NC}"
        dc build
        echo -e "${GREEN}Build complete${NC}"
        ;;
    pull)
        echo -e "${BLUE}Pulling latest images...${NC}"
        dc pull
        echo -e "${GREEN}Pull complete${NC}"
        ;;
    shell)
        echo -e "${BLUE}Opening shell in backend container...${NC}"
        if [[ "$PROFILE" == "gpu" ]]; then
            dc exec mem-backend /bin/bash
        else
            dc exec mem-backend-cpu /bin/bash
        fi
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
