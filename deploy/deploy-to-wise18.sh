#!/usr/bin/env bash
# Deploy Mem to wise18.tap NixOS server

set -e

# Configuration
REMOTE_HOST="wise18.tap"
REMOTE_USER="sdelcore"
REMOTE_PASS="asd"
REGISTRY="registry.sdelcore.com"
PROJECT="mem"
TAG="${1:-latest}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "${BLUE}    🚀 Deploying Mem to wise18.tap${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}\n"

# Create deployment directory structure on remote
echo -e "${YELLOW}Creating remote directories...${NC}"
sshpass -p "${REMOTE_PASS}" ssh "${REMOTE_USER}@${REMOTE_HOST}" << 'EOF'
mkdir -p ~/mem-deployment/{data/{db,uploads,config,streams},logs}
EOF

# Copy configuration files
echo -e "${YELLOW}Copying configuration files...${NC}"
sshpass -p "${REMOTE_PASS}" scp docker-compose.yml "${REMOTE_USER}@${REMOTE_HOST}:~/mem-deployment/"
sshpass -p "${REMOTE_PASS}" scp mem/config.yaml "${REMOTE_USER}@${REMOTE_HOST}:~/mem-deployment/data/config/"

# Create docker-compose override for production
echo -e "${YELLOW}Creating production override...${NC}"
cat > docker-compose.prod.yml << EOF
version: '3.8'

services:
  mem-backend:
    image: ${REGISTRY}/${PROJECT}/backend:${TAG}
    volumes:
      - /home/${REMOTE_USER}/mem-deployment/data/db:/data/db
      - /home/${REMOTE_USER}/mem-deployment/data/uploads:/data/uploads
      - /home/${REMOTE_USER}/mem-deployment/data/config:/app/config:ro
      - whisper-models:/home/memuser/.cache/huggingface
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"

  mem-frontend:
    image: ${REGISTRY}/${PROJECT}/frontend:${TAG}
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"

  mem-rtmp:
    image: ${REGISTRY}/${PROJECT}/rtmp:${TAG}
    volumes:
      - /home/${REMOTE_USER}/mem-deployment/data/streams:/data/streams
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"
EOF

sshpass -p "${REMOTE_PASS}" scp docker-compose.prod.yml "${REMOTE_USER}@${REMOTE_HOST}:~/mem-deployment/"

# Deploy on remote server
echo -e "${YELLOW}Deploying on wise18.tap...${NC}"
sshpass -p "${REMOTE_PASS}" ssh "${REMOTE_USER}@${REMOTE_HOST}" << EOF
cd ~/mem-deployment

# Login to registry
echo "${REMOTE_PASS}" | sudo -S docker login ${REGISTRY} -u ${REMOTE_USER} --password-stdin

# Pull latest images
echo -e "${YELLOW}Pulling latest images...${NC}"
sudo docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull

# Stop existing containers
echo -e "${YELLOW}Stopping existing services...${NC}"
sudo docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# Start new containers
echo -e "${GREEN}Starting services...${NC}"
sudo docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Show status
echo -e "${GREEN}Service status:${NC}"
sudo docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps

# Show logs
echo -e "${YELLOW}Recent logs:${NC}"
sudo docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=20
EOF

# Get server IP
SERVER_IP=$(sshpass -p "${REMOTE_PASS}" ssh "${REMOTE_USER}@${REMOTE_HOST}" "hostname -I | awk '{print \$1}'")

echo -e "\n${GREEN}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}    ✅ Deployment Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════${NC}\n"

echo -e "${BLUE}Access Points:${NC}"
echo -e "  ${YELLOW}Frontend:${NC} http://${SERVER_IP}"
echo -e "  ${YELLOW}Backend API:${NC} http://${SERVER_IP}:8000"
echo -e "  ${YELLOW}API Docs:${NC} http://${SERVER_IP}:8000/docs"
echo -e "  ${YELLOW}RTMP Stream:${NC} rtmp://${SERVER_IP}:1935/live"

echo -e "\n${BLUE}Monitoring:${NC}"
echo -e "  SSH to server: sshpass -p ${REMOTE_PASS} ssh ${REMOTE_USER}@${REMOTE_HOST}"
echo -e "  View logs: sudo docker-compose logs -f"
echo -e "  Service status: sudo docker-compose ps"

echo -e "\n${YELLOW}GPU Status:${NC}"
sshpass -p "${REMOTE_PASS}" ssh "${REMOTE_USER}@${REMOTE_HOST}" "nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader"