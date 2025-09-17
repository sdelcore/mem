# Mem Deployment Guide

This guide covers deploying Mem to your NixOS server (wise18.tap) with GPU support for Faster-Whisper.

## Prerequisites

- Docker and docker-compose installed on wise18.tap
- NVIDIA drivers and nvidia-docker runtime configured
- Access to registry.sdelcore.com
- SSH access to wise18.tap (user: sdelcore, password: asd)

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  wise18.tap (NixOS)                  │
│                                                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐   │
│  │  Frontend  │  │   Backend  │  │    RTMP    │   │
│  │   (nginx)  │──│ (FastAPI)  │──│   Server   │   │
│  │   Port 80  │  │  Port 8000 │  │  Port 1935 │   │
│  └────────────┘  └─────┬──────┘  └────────────┘   │
│                        │                            │
│                 ┌──────┴───────┐                    │
│                 │ GTX 1080 Ti  │                    │
│                 │ Faster-Whisper│                    │
│                 └──────────────┘                    │
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

### 2. Deploy to wise18.tap

```bash
./deploy/deploy-to-wise18.sh
```

This will:
- SSH to wise18.tap
- Pull the latest images
- Start all services with docker-compose
- Configure GPU passthrough for Faster-Whisper

## Manual Deployment Steps

### 1. Build Images Locally

```bash
# Backend with GPU support
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

SSH to the server:
```bash
ssh sdelcore@wise18.tap
# Password: asd
```

Create deployment directory:
```bash
mkdir -p ~/mem-deployment/{data/{db,uploads,config,streams},logs}
```

Copy docker-compose files:
```bash
# From local machine
scp docker-compose.yml docker-compose.prod.yml sdelcore@wise18.tap:~/mem-deployment/
scp mem/config.yaml sdelcore@wise18.tap:~/mem-deployment/data/config/
```

Start services:
```bash
cd ~/mem-deployment
sudo docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Configuration

### GPU Settings

The GTX 1080 Ti is configured for Faster-Whisper with:
- Device: cuda
- Compute Type: float16 (optimal for 1080 Ti)
- Model: base (can be changed to tiny, small, medium, or large)

Edit `data/config/config.yaml`:
```yaml
whisper:
  model: base  # Options: tiny, base, small, medium, large
  device: cuda
  compute_type: float16  # float16 for GPU, int8 for CPU
```

### Memory Requirements

- tiny: ~39MB VRAM
- base: ~74MB VRAM
- small: ~244MB VRAM
- medium: ~769MB VRAM
- large: ~1550MB VRAM

The GTX 1080 Ti with 11GB VRAM can handle all models comfortably.

## Service Management

### Check Status
```bash
sudo docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

### View Logs
```bash
# All services
sudo docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# Specific service
sudo docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f mem-backend
```

### Restart Services
```bash
sudo docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart
```

### Stop Services
```bash
sudo docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
```

### GPU Monitoring
```bash
nvidia-smi
# or watch GPU usage
watch -n 1 nvidia-smi
```

## Systemd Service (Optional)

To auto-start Mem on boot:

1. Copy service file:
```bash
sudo cp deploy/mem.service /etc/systemd/system/
```

2. Enable service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mem.service
sudo systemctl start mem.service
```

3. Check status:
```bash
sudo systemctl status mem.service
```

## Access Points

After deployment, access the services at:

- **Frontend**: http://wise18.tap or http://[SERVER_IP]
- **Backend API**: http://wise18.tap:8000
- **API Documentation**: http://wise18.tap:8000/docs
- **RTMP Streaming**: rtmp://wise18.tap:1935/live

## Streaming with OBS

1. Open OBS Studio
2. Settings → Stream
3. Service: Custom
4. Server: `rtmp://wise18.tap:1935/live`
5. Stream Key: (get from API or use any unique key)

## Troubleshooting

### Container Won't Start
```bash
# Check logs
sudo docker-compose logs mem-backend

# Check GPU availability
nvidia-smi
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### GPU Not Available
```bash
# Check nvidia-docker runtime
sudo docker info | grep nvidia

# Test GPU access
docker run --rm --runtime=nvidia nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
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

# Check firewall
sudo iptables -L -n
```

## Performance Tuning

### Faster-Whisper Optimization

For best performance on GTX 1080 Ti:

1. Use `float16` compute type (default)
2. Adjust beam size in transcriber.py for speed vs accuracy
3. Enable VAD (Voice Activity Detection) to skip silence

### Database Optimization

DuckDB is already optimized, but you can tune:
```yaml
database:
  memory_limit: 4GB  # Adjust based on available RAM
  threads: 8         # Number of threads for queries
```

## Backup and Restore

### Backup Database
```bash
# On wise18.tap
cd ~/mem-deployment
sudo docker-compose exec mem-backend python -c "
import duckdb
conn = duckdb.connect('/data/db/mem.duckdb')
conn.execute('EXPORT DATABASE \'/data/db/backup\' (FORMAT PARQUET)')
"
tar -czf mem-backup-$(date +%Y%m%d).tar.gz data/db/backup/
```

### Restore Database
```bash
tar -xzf mem-backup-20240101.tar.gz
sudo docker-compose exec mem-backend python -c "
import duckdb
conn = duckdb.connect('/data/db/mem-restored.duckdb')
conn.execute('IMPORT DATABASE \'/data/db/backup\'')
"
```

## Security Notes

1. Change default password on wise18.tap
2. Configure firewall rules for production
3. Use HTTPS with proper certificates
4. Rotate stream keys regularly
5. Monitor access logs

## Support

For issues or questions:
1. Check container logs
2. Verify GPU access
3. Ensure all ports are accessible
4. Review this documentation