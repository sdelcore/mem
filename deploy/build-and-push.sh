#!/usr/bin/env bash
# Build and push Docker images to registry.sdelcore.com

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

REGISTRY="registry.sdelcore.com"
PROJECT="mem"
TAG="${1:-latest}"

echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "${BLUE}    🚀 Mem Docker Build & Push Script${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}\n"

echo -e "${YELLOW}Registry: ${REGISTRY}${NC}"
echo -e "${YELLOW}Tag: ${TAG}${NC}\n"

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

# Build and push backend
echo -e "\n${BLUE}[1/3] Backend Service${NC}"
build_and_push "backend" "./mem" "./mem/Dockerfile"

# Build and push frontend
echo -e "${BLUE}[2/3] Frontend Service${NC}"
build_and_push "frontend" "./mem-ui" "./mem-ui/Dockerfile"

# Build and push RTMP server
echo -e "${BLUE}[3/3] RTMP Service${NC}"
build_and_push "rtmp" "./rtmp" "./rtmp/Dockerfile"

echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}    ✅ All images built and pushed successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════${NC}\n"

echo -e "${YELLOW}Images pushed:${NC}"
echo -e "  • ${REGISTRY}/${PROJECT}/backend:${TAG}"
echo -e "  • ${REGISTRY}/${PROJECT}/frontend:${TAG}"
echo -e "  • ${REGISTRY}/${PROJECT}/rtmp:${TAG}"

echo -e "\n${BLUE}Next steps:${NC}"
echo -e "  1. SSH to wise18.tap"
echo -e "  2. Run: ./deploy/deploy-to-wise18.sh"