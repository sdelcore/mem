# Mem Deployment Guide

This guide covers deploying Mem to your server with STTD transcription service.

## Prerequisites

- Docker and docker-compose installed
- Access to registry.sdelcore.com (or your own registry)
- STTD service running on a network host (for transcription)

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  Deployment Server                   │
│                                                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐   │
│  │  Frontend  │  │   Backend  │  │    RTMP    │   │
│  │   (nginx)  │──│ (FastAPI)  │──│   Server   │   │
│  │   Port 80  │  │  Port 8000 │  │  Port 1935 │   │
│  └────────────┘  └─────┬──────┘  └────────────┘   │
│                        │                            │
└────────────────────────┼────────────────────────────┘
                         │ HTTP API
                         ▼
┌─────────────────────────────────────────────────────┐
│              STTD Server (Network Host)              │
│  ┌────────────────────────────────────────────┐    │
│  │ STTD Service - Port 8765                   │    │
│  │ • Transcription (speech-to-text)           │    │
│  │ • Speaker diarization                      │    │
│  │ • Voice profile management                 │    │
│  └────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

## Quick Deployment

### 1. Build and Push Images (from local machine)

```bash
cd /home/sdelcore/src/mem
./deploy/build-and-push.sh
```

This will:
- Build Docker images for backend, frontend, and RTMP server
- Push them to registry.sdelcore.com

### 2. Deploy to Server

```bash
./deploy/deploy-to-wise18.sh
```

This will:
- SSH to the server
- Pull the latest images
- Start all services with docker-compose

## Manual Deployment Steps

### 1. Build Images Locally

```bash
# Backend
docker build -t registry.sdelcore.com/mem/backend:latest -f mem/Dockerfile ./mem

# Frontend
docker build -t registry.sdelcore.com/mem/frontend:latest -f mem-ui/Dockerfile ./mem-ui

# RTMP Server
docker build -t registry.sdelcore.com/mem/rtmp:latest -f rtmp/Dockerfile ./rtmp
```

### 2. Push to Registry

```bash
docker login registry.sdelcore.com
docker push registry.sdelcore.com/mem/backend:latest
docker push registry.sdelcore.com/mem/frontend:latest
docker push registry.sdelcore.com/mem/rtmp:latest
```

### 3. Deploy on Server

Create deployment directory:
```bash
mkdir -p ~/mem-deployment/{data/{db,uploads,config,streams},logs}
```

Copy config file and customize:
```bash
scp mem/config.yaml user@server:~/mem-deployment/data/config/
```

Start services:
```bash
cd ~/mem-deployment
docker compose up -d
```

## Configuration

### STTD Settings

Configure the connection to your STTD service in `config.yaml`:
```yaml
sttd:
  host: "sttd-server.local"   # Hostname of STTD service
  port: 8765                  # STTD HTTP port
  timeout: 300.0              # Request timeout in seconds
  identify_speakers: true     # Enable speaker identification
```

### Capture Settings

```yaml
capture:
  frame:
    interval_seconds: 5       # Frame extraction interval
    jpeg_quality: 85          # JPEG compression quality
    enable_deduplication: true
    similarity_threshold: 95.0
  audio:
    chunk_duration_seconds: 60  # Audio chunk duration
    overlap_seconds: 5          # Overlap between chunks
    sample_rate: 16000
```

### Streaming Settings

```yaml
streaming:
  rtmp:
    enabled: true
    host: "server.example.com"  # External hostname for RTMP URLs
    port: 1935
    max_concurrent_streams: 10
```

## STTD Service Setup

STTD runs as a systemd user service. On your STTD host:

### Start the Service
```bash
systemctl --user start sttd-server
```

### Enable on Boot
```bash
systemctl --user enable sttd-server
```

### Check Status
```bash
systemctl --user status sttd-server
curl http://localhost:8765/health
```

## Service Management

### Check Status
```bash
docker compose ps
```

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f mem-backend
```

### Restart Services
```bash
docker compose restart
```

### Stop Services
```bash
docker compose down
```

## Access Points

After deployment:

- **Frontend**: http://server.example.com
- **Backend API**: http://server.example.com:8000
- **API Documentation**: http://server.example.com:8000/docs
- **RTMP Streaming**: rtmp://server.example.com:1935/live

## Streaming with OBS

1. Open OBS Studio
2. Settings → Stream
3. Service: Custom
4. Server: `rtmp://server.example.com:1935/live`
5. Stream Key: Get from API (`POST /api/streams/create`)

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker compose logs mem-backend
```

### Transcription Fails
```bash
# Check STTD connectivity
curl http://sttd-server:8765/health

# Check backend logs for STTD errors
docker compose logs mem-backend | grep -i sttd
```

### Permission Issues
```bash
# Fix volume permissions
sudo chown -R 1000:1000 ~/mem-deployment/data
```

### Network Issues
```bash
# Check if ports are open
sudo netstat -tlnp | grep -E '(80|8000|1935)'
```

## Backup and Restore

### Backup Database
```bash
cd ~/mem-deployment
./scripts/backup.sh
```

### Restore Database
```bash
./scripts/restore.sh backup-20240101.tar.gz
```

## Security Notes

1. Configure firewall rules for production
2. Use HTTPS with proper certificates (via reverse proxy)
3. Rotate stream keys regularly
4. Monitor access logs
5. Keep STTD service on internal network if possible
