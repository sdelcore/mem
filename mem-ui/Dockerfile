# Multi-stage Dockerfile for Mem frontend

# Stage 1: Builder
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies (including dev deps needed for build)
RUN npm ci && \
    npm cache clean --force

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Stage 2: Runtime with nginx
FROM nginx:alpine

# Install runtime dependencies
RUN apk add --no-cache \
    curl \
    tini \
    openssl

# Generate self-signed SSL certificate for local network access
RUN mkdir -p /etc/nginx/ssl && \
    openssl req -x509 -nodes -days 365 \
      -subj "/CN=mem-local" \
      -newkey rsa:2048 \
      -keyout /etc/nginx/ssl/server.key \
      -out /etc/nginx/ssl/server.crt && \
    chmod 600 /etc/nginx/ssl/server.key

# Remove default nginx config
RUN rm -rf /etc/nginx/conf.d/*

# Create nginx config for SPA
COPY --chown=nginx:nginx nginx.conf /etc/nginx/conf.d/default.conf

# Copy built application from builder
COPY --from=builder --chown=nginx:nginx /app/dist /usr/share/nginx/html

# Create non-root user permissions
RUN chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d && \
    chown -R nginx:nginx /etc/nginx/ssl && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

# Switch to non-root user
USER nginx

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

# Expose ports (HTTP and HTTPS)
EXPOSE 80 443

# Use tini for proper signal handling
ENTRYPOINT ["/sbin/tini", "--"]

# Start nginx
CMD ["nginx", "-g", "daemon off;"]