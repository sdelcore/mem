# Operations Guide

## Deployment

### Prerequisites
- Python 3.9
- FFmpeg 
- 4GB+ RAM for Whisper models
- 10GB+ disk space for database growth

### Production Deployment

#### Docker Deployment (Recommended)
```bash
# Build container (Dockerfile not yet available - planned)
docker build -t mem:latest .

# Run with volume mounts
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/mem.duckdb:/app/mem.duckdb \
  --name mem-api \
  mem:latest
```

#### Systemd Service
```ini
# /etc/systemd/system/mem-api.service
[Unit]
Description=Mem Video Processing API
After=network.target

[Service]
Type=simple
User=mem
WorkingDirectory=/opt/mem
Environment="PATH=/opt/mem/.venv/bin"
ExecStart=/opt/mem/.venv/bin/uvicorn src.api.app:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Nginx Reverse Proxy
```nginx
server {
    listen 443 ssl http2;
    server_name mem.example.com;

    ssl_certificate /etc/ssl/certs/mem.crt;
    ssl_certificate_key /etc/ssl/private/mem.key;

    client_max_body_size 5G;  # Match API max_upload_size

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for large video processing
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
    }
}
```

## Monitoring

### Health Checks
```bash
# Basic health check
curl http://localhost:8000/api/status

# Detailed system status
curl http://localhost:8000/api/status | jq '.'
```

### Key Metrics to Monitor
- **Database size**: Monitor `mem.duckdb` growth
- **Frame deduplication rate**: Should be ~90%
- **Job queue length**: Track processing backlog
- **API response times**: Especially for search queries
- **Disk usage**: Both database and temp files
- **Memory usage**: Whisper models consume significant RAM

### Logging
```python
# Application logs location
/var/log/mem/api.log     # API server logs
/var/log/mem/capture.log # Video processing logs

# Log rotation config
/etc/logrotate.d/mem:
/var/log/mem/*.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
}
```

## Backup & Recovery

### Database Backup
```bash
# Hot backup (while running)
echo ".backup '/backup/mem_$(date +%Y%m%d).duckdb'" | duckdb mem.duckdb

# Scheduled backup via cron
0 2 * * * /usr/local/bin/backup-mem.sh
```

### Recovery Procedure
1. Stop API service
2. Restore database file
3. Verify integrity: `duckdb mem.duckdb "PRAGMA integrity_check;"`
4. Restart API service

## Performance Tuning

### Database Optimization
```sql
-- Analyze tables for query optimization
ANALYZE;

-- Vacuum to reclaim space
VACUUM;

-- Check index usage
SELECT * FROM duckdb_indexes();
```

### API Configuration
```yaml
# config.yaml tuning for production
api:
  max_upload_size: 10737418240  # 10GB for larger videos
  default_time_range_days: 7    # Increase for better UX

capture:
  frame:
    interval_seconds: 10         # Reduce for lower storage
    jpeg_quality: 80            # Balance quality/size

whisper:
  model: "small"                # Better accuracy in production
  device: "cuda"                # Use GPU if available
```

### Resource Limits
```bash
# Systemd resource limits
[Service]
LimitNOFILE=65536          # File descriptors
MemoryLimit=8G             # RAM limit
CPUQuota=200%              # 2 CPU cores max
```

## Troubleshooting

### Common Issues

#### 1. Out of Memory During Transcription
**Symptom**: Process killed during audio processing
**Solution**: 
- Use smaller Whisper model (tiny/base)
- Increase system RAM
- Add swap space

#### 2. Database Lock Errors
**Symptom**: "database is locked" errors
**Solution**:
- Ensure single writer process
- Increase busy timeout: `PRAGMA busy_timeout = 5000;`
- Check for zombie connections

#### 3. Slow Frame Extraction
**Symptom**: Video processing takes hours
**Solution**:
- Increase frame interval in config
- Check FFmpeg installation
- Use SSD for temp storage

#### 4. API Timeouts
**Symptom**: 504 Gateway Timeout on large videos
**Solution**:
- Increase proxy timeouts (see Nginx config)
- Implement async job processing (planned)
- Split large videos before upload

### Debug Commands
```bash
# Check database integrity
duckdb mem.duckdb "PRAGMA integrity_check;"

# View active connections
lsof | grep mem.duckdb

# Check disk usage
du -sh data/* mem.duckdb

# Monitor API logs
tail -f /var/log/mem/api.log | grep ERROR

# Test video processing
uv run python -m src.capture.pipeline data/test_videos/test.mp4
```

## Security Hardening

### API Security
```python
# Add to src/api/app.py
from fastapi import HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # Implement token validation
    if not valid_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
```

### File Upload Security
- Validate file content, not just extension
- Scan for malware (ClamAV integration)
- Limit concurrent uploads per IP
- Implement rate limiting

### Database Security
```bash
# Encrypt database at rest
# Use filesystem encryption (LUKS, FileVault)

# Restrict database file permissions
chmod 600 mem.duckdb
chown mem:mem mem.duckdb
```

## Scaling Considerations

### Horizontal Scaling (Planned)
- Implement job queue (Redis/Celery)
- Separate API from processing workers
- Use shared storage (NFS/S3) for videos
- Consider PostgreSQL for multi-writer support

### Performance Benchmarks
| Metric | Current | Target | Method |
|--------|---------|--------|--------|
| Video processing | 1x realtime | 5x realtime | Parallel extraction |
| Search latency | <100ms | <50ms | Query caching |
| Deduplication rate | 90% | 95% | Better hash algorithm |
| Database size | 120MB/day | 60MB/day | Compression |

## Maintenance Tasks

### Daily
- Check disk space
- Review error logs
- Verify backup completion

### Weekly  
- Database optimization (VACUUM/ANALYZE)
- Clear temp files
- Review job failure rate

### Monthly
- Security updates
- Performance analysis
- Capacity planning review