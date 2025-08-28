#!/usr/bin/env bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Trap function to kill both processes on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    
    if [[ -n $BACKEND_PID ]]; then
        echo -e "${RED}Stopping backend (PID: $BACKEND_PID)...${NC}"
        kill $BACKEND_PID 2>/dev/null
        wait $BACKEND_PID 2>/dev/null
    fi
    
    if [[ -n $FRONTEND_PID ]]; then
        echo -e "${RED}Stopping frontend (PID: $FRONTEND_PID)...${NC}"
        kill $FRONTEND_PID 2>/dev/null
        wait $FRONTEND_PID 2>/dev/null
    fi
    
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}

# Set up trap for clean exit
trap cleanup SIGINT SIGTERM EXIT

echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "${BLUE}       🎬 Mem Full Stack Launcher${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}\n"

# Get local IP address for external access
LOCAL_IP=$(hostname -I | awk '{print $1}')
if [[ -z "$LOCAL_IP" ]]; then
    LOCAL_IP="127.0.0.1"
fi

echo -e "${YELLOW}Starting Mem services...${NC}"
echo -e "${BLUE}Local IP: ${LOCAL_IP}${NC}\n"

# Start backend
echo -e "${GREEN}Starting backend API server...${NC}"
cd /home/sdelcore/src/mem/mem
nix develop -c uv run uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000 > /tmp/mem-backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}Backend started with PID: $BACKEND_PID${NC}"

# Wait a bit for backend to start
sleep 3

# Check if backend started successfully
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}Backend failed to start! Check /tmp/mem-backend.log${NC}"
    exit 1
fi

# Start frontend
echo -e "${GREEN}Starting frontend development server...${NC}"
cd /home/sdelcore/src/mem/mem-ui
npm run dev -- --host 0.0.0.0 --port 3000 > /tmp/mem-frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}Frontend started with PID: $FRONTEND_PID${NC}"

# Wait a bit for frontend to start
sleep 3

# Check if frontend started successfully
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${RED}Frontend failed to start! Check /tmp/mem-frontend.log${NC}"
    exit 1
fi

echo -e "\n${GREEN}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}       ✅ All services started successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════${NC}\n"

echo -e "${BLUE}Access points:${NC}"
echo -e "  ${YELLOW}Frontend:${NC}"
echo -e "    • Local:    http://localhost:3000"
echo -e "    • Network:  http://${LOCAL_IP}:3000"
echo -e "  ${YELLOW}Backend API:${NC}"
echo -e "    • Local:    http://localhost:8000"
echo -e "    • Network:  http://${LOCAL_IP}:8000"
echo -e "    • Swagger:  http://${LOCAL_IP}:8000/docs"
echo -e "\n${YELLOW}Logs:${NC}"
echo -e "  • Backend:  tail -f /tmp/mem-backend.log"
echo -e "  • Frontend: tail -f /tmp/mem-frontend.log"
echo -e "\n${RED}Press Ctrl+C to stop all services${NC}\n"

# Monitor processes
while true; do
    # Check if backend is still running
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e "${RED}Backend process died unexpectedly!${NC}"
        echo -e "${YELLOW}Check logs: tail -f /tmp/mem-backend.log${NC}"
        cleanup
    fi
    
    # Check if frontend is still running
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo -e "${RED}Frontend process died unexpectedly!${NC}"
        echo -e "${YELLOW}Check logs: tail -f /tmp/mem-frontend.log${NC}"
        cleanup
    fi
    
    sleep 5
done