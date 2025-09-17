# Dockerfile for RTMP streaming server
FROM tiangolo/nginx-rtmp:latest

# Install additional dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Create directories
RUN mkdir -p /data/streams /var/log/nginx

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy stream handler script
COPY stream_handler.py /usr/local/bin/stream_handler.py
RUN chmod +x /usr/local/bin/stream_handler.py

# Install Python dependencies for stream handler
RUN pip3 install httpx

# Expose RTMP port
EXPOSE 1935

# Expose HTTP stats port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD nc -z localhost 1935 || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]