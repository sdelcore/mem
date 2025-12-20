#!/usr/bin/env bash
# Build and push Docker images to registry.sdelcore.com
# Usage:
#   ./build-and-push.sh [tag] [options]
#   ./build-and-push.sh latest --all       # Build everything (default)
#   ./build-and-push.sh latest --gpu-only  # GPU backend only
#   ./build-and-push.sh latest --cpu-only  # CPU backend only
#   ./build-and-push.sh latest --no-backend # Frontend and RTMP only

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

REGISTRY="registry.sdelcore.com"
PROJECT="mem"

# Default options
TAG="latest"
BUILD_GPU=true
BUILD_CPU=true
BUILD_FRONTEND=true
BUILD_RTMP=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            BUILD_GPU=true
            BUILD_CPU=true
            BUILD_FRONTEND=true
            BUILD_RTMP=true
            shift
            ;;
        --gpu-only)
            BUILD_GPU=true
            BUILD_CPU=false
            BUILD_FRONTEND=false
            BUILD_RTMP=false
            shift
            ;;
        --cpu-only)
            BUILD_GPU=false
            BUILD_CPU=true
            BUILD_FRONTEND=false
            BUILD_RTMP=false
            shift
            ;;
        --no-backend)
            BUILD_GPU=false
            BUILD_CPU=false
            shift
            ;;
        --backend-only)
            BUILD_GPU=true
            BUILD_CPU=true
            BUILD_FRONTEND=false
            BUILD_RTMP=false
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [tag] [options]"
            echo ""
            echo "Arguments:"
            echo "  tag           Image tag (default: latest)"
            echo ""
            echo "Options:"
            echo "  --all         Build all images (default)"
            echo "  --gpu-only    Build only GPU backend"
            echo "  --cpu-only    Build only CPU backend"
            echo "  --backend-only Build both GPU and CPU backends"
            echo "  --no-backend  Build frontend and RTMP only"
            echo "  --help        Show this help"
            exit 0
            ;;
        *)
            # Assume it's the tag if it doesn't start with --
            if [[ ! "$1" =~ ^-- ]]; then
                TAG="$1"
            else
                echo -e "${RED}Unknown option: $1${NC}"
                exit 1
            fi
            shift
            ;;
    esac
done

echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "${BLUE}    Mem Docker Build & Push Script${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}\n"

echo -e "${YELLOW}Registry: ${REGISTRY}${NC}"
echo -e "${YELLOW}Tag: ${TAG}${NC}"
echo -e "${CYAN}Build GPU Backend: ${BUILD_GPU}${NC}"
echo -e "${CYAN}Build CPU Backend: ${BUILD_CPU}${NC}"
echo -e "${CYAN}Build Frontend: ${BUILD_FRONTEND}${NC}"
echo -e "${CYAN}Build RTMP: ${BUILD_RTMP}${NC}\n"

# Function to build and push an image
build_and_push() {
    local service=$1
    local context=$2
    local dockerfile=$3
    local image="${REGISTRY}/${PROJECT}/${service}:${TAG}"

    echo -e "${GREEN}Building ${service}...${NC}"
    docker build -t "${image}" -f "${dockerfile}" "${context}"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Build successful${NC}"

        echo -e "${YELLOW}Pushing ${image}...${NC}"
        docker push "${image}"

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Push successful${NC}\n"
        else
            echo -e "${RED}✗ Push failed${NC}\n"
            exit 1
        fi
    else
        echo -e "${RED}✗ Build failed${NC}\n"
        exit 1
    fi
}

# Check if docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed or not in PATH${NC}"
    exit 1
fi

# Login to registry
echo -e "${YELLOW}Logging in to ${REGISTRY}...${NC}"
docker login "${REGISTRY}"

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to login to registry${NC}"
    exit 1
fi

# Track what we're building
STEP=1
TOTAL=0
[[ "$BUILD_GPU" == "true" ]] && ((TOTAL++))
[[ "$BUILD_CPU" == "true" ]] && ((TOTAL++))
[[ "$BUILD_FRONTEND" == "true" ]] && ((TOTAL++))
[[ "$BUILD_RTMP" == "true" ]] && ((TOTAL++))

if [[ $TOTAL -eq 0 ]]; then
    echo -e "${YELLOW}Nothing to build. Use --help for options.${NC}"
    exit 0
fi

PUSHED_IMAGES=()

# Build and push GPU backend
if [[ "$BUILD_GPU" == "true" ]]; then
    echo -e "\n${BLUE}[${STEP}/${TOTAL}] Backend Service (GPU)${NC}"
    build_and_push "backend" "./mem" "./mem/Dockerfile"
    PUSHED_IMAGES+=("${REGISTRY}/${PROJECT}/backend:${TAG}")
    ((STEP++))
fi

# Build and push CPU backend
if [[ "$BUILD_CPU" == "true" ]]; then
    echo -e "\n${BLUE}[${STEP}/${TOTAL}] Backend Service (CPU)${NC}"
    build_and_push "backend-cpu" "./mem" "./mem/Dockerfile.cpu"
    PUSHED_IMAGES+=("${REGISTRY}/${PROJECT}/backend-cpu:${TAG}")
    ((STEP++))
fi

# Build and push frontend
if [[ "$BUILD_FRONTEND" == "true" ]]; then
    echo -e "${BLUE}[${STEP}/${TOTAL}] Frontend Service${NC}"
    build_and_push "frontend" "./mem-ui" "./mem-ui/Dockerfile"
    PUSHED_IMAGES+=("${REGISTRY}/${PROJECT}/frontend:${TAG}")
    ((STEP++))
fi

# Build and push RTMP server
if [[ "$BUILD_RTMP" == "true" ]]; then
    echo -e "${BLUE}[${STEP}/${TOTAL}] RTMP Service${NC}"
    build_and_push "rtmp" "./rtmp" "./rtmp/Dockerfile"
    PUSHED_IMAGES+=("${REGISTRY}/${PROJECT}/rtmp:${TAG}")
    ((STEP++))
fi

echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}    All images built and pushed successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════${NC}\n"

echo -e "${YELLOW}Images pushed:${NC}"
for img in "${PUSHED_IMAGES[@]}"; do
    echo -e "  - ${img}"
done

echo -e "\n${BLUE}Next steps:${NC}"
echo -e "  1. SSH to deployment target"
echo -e "  2. Run: ./run.sh [gpu|cpu] up"