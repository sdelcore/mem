#!/usr/bin/env bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping Mem services...${NC}"

# Stop any npm dev servers on port 3000
echo -e "${RED}Stopping frontend...${NC}"
lsof -ti:3000 | xargs -r kill -9 2>/dev/null
pkill -f "npm.*dev" 2>/dev/null
pkill -f "vite" 2>/dev/null

# Stop any uvicorn servers on port 8000
echo -e "${RED}Stopping backend...${NC}"
lsof -ti:8000 | xargs -r kill -9 2>/dev/null
pkill -f "uvicorn.*8000" 2>/dev/null

echo -e "${GREEN}All services stopped.${NC}"