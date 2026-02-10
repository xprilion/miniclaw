# Production Deployment Guide

This guide covers deploying MiniClaw in production environments with emphasis on security, reliability, and scalability.

## Prerequisites

- Linux server (Ubuntu 20.04+ recommended)
- Python 3.9+
- Docker (optional, for containerized deployment)
- Reverse proxy (nginx, Apache, or cloud load balancer)
- SSL certificate (Let's Encrypt recommended)

## Deployment Options

### 1. Direct Installation

For simple deployments on a single server:

```bash
# Create dedicated user
sudo useradd -m -s /bin/bash miniclaw
sudo su - miniclaw

# Clone repository
git clone <repo-url>
cd miniclaw

# Install dependencies
pip install -e .

# Create production configuration
mkdir -p ~/.miniclaw
cp miniclaw_config.example.json ~/.miniclaw/miniclaw_config.json
```

### 2. Docker Deployment

Docker deployment is the recommended approach for production environments as it provides better isolation, easier management, and consistent behavior across different environments.

#### Prerequisites for Docker Deployment

- Docker 20.04+ installed on the host system
- Docker Compose (optional but recommended)

#### Optimized Dockerfile

Create a `Dockerfile` at the root of your repository:

```dockerfile
FROM python:3.11-slim

# Set environment variables
ENV MINICLAW_HOST=0.0.0.0
ENV MINICLAW_PORT=8787
ENV MINICLAW_WORKSPACE=/home/miniclaw/.miniclaw
ENV PATH="/home/miniclaw/.local/bin:${PATH}"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash miniclaw

USER miniclaw
WORKDIR /home/miniclaw

# Copy local code instead of cloning
COPY --chown=miniclaw:miniclaw . /home/miniclaw/miniclaw

WORKDIR /home/miniclaw/miniclaw

# Install MiniClaw in development mode
RUN python -m pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Create workspace directory
RUN mkdir -p /home/miniclaw/.miniclaw

# Expose the default port
EXPOSE 8787

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8787/api/health || exit 1

# Run MiniClaw server
CMD ["python", "-c", "from miniclaw import run; run()"]
```

#### Docker Ignore File

Create a `.dockerignore` file to exclude unnecessary files from the build context:

```gitignore
.git
.gitignore
.coverage
__pycache__
*.pyc
.venv/
venv/
.DS_Store
*.log
build/
dist/
*.egg-info/
htmlcov/
.env
.env.local
.env.development.local
.env.test.local
.env.production.local
frontend/node_modules/
frontend/dist/
tmp/
tests/
*.md
!.github/
!.gitlab/

# Exclude local data that shouldn't be in the image
.miniclaw/
```

#### Building the Docker Image

```bash
# Build the Docker image
docker build -t miniclaw .

# Verify the image was built successfully
docker images | grep miniclaw
```

#### Running MiniClaw Container

Basic container run:

```bash
docker run -d \
  --name miniclaw \
  -p 8787:8787 \
  -v miniclaw_data:/home/miniclaw/.miniclaw \
  miniclaw
```

### 3. Docker Compose Deployment (Recommended)

Docker Compose provides the easiest way to manage MiniClaw with all its dependencies and configurations.

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  miniclaw:
    build: .
    container_name: miniclaw
    ports:
      - "8787:8787"
    environment:
      - MINICLAW_HOST=0.0.0.0
      - MINICLAW_PORT=8787
    volumes:
      - miniclaw_data:/home/miniclaw/.miniclaw
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8787/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

volumes:
  miniclaw_data:
```

#### Advanced Docker Compose Configuration

For production environments with more complex requirements:

```yaml
version: '3.8'

services:
  miniclaw:
    build: .
    container_name: miniclaw
    ports:
      - "8787:8787"
    environment:
      - MINICLAW_HOST=0.0.0.0
      - MINICLAW_PORT=8787
      # Configure your model provider
      - PROVIDER_BASE_URL=https://api.inference.wandb.ai/v1
      - PROVIDER_MODEL=Qwen/Qwen3-235B-A22B-Thinking-2507
      - PROVIDER_API_KEY=your-api-key-here
    volumes:
      - miniclaw_data:/home/miniclaw/.miniclaw
      # Mount custom configuration if needed
      # - ./custom_config.json:/home/miniclaw/.miniclaw/miniclaw_config.json
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8787/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    # Resource limits
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'

volumes:
  miniclaw_data:
```

#### Docker Compose Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Update and restart
docker-compose up -d --build

# Check service status
docker-compose ps
```

### 4. Custom Configuration in Docker

#### Environment Variables

MiniClaw supports several environment variables for configuration:

```bash
docker run -d \
  --name miniclaw \
  -p 8787:8787 \
  -e MINICLAW_HOST=0.0.0.0 \
  -e MINICLAW_PORT=8787 \
  -e MINICLAW_WORKSPACE=/home/miniclaw/.miniclaw \
  -e PROVIDER_BASE_URL=https://api.inference.wandb.ai/v1 \
  -e PROVIDER_MODEL=Qwen/Qwen3-235B-A22B-Thinking-2507 \
  -v miniclaw_data:/home/miniclaw/.miniclaw \
  miniclaw
```

#### Custom Configuration File

To use a custom configuration file:

```bash
# Create a custom config file
echo '{
  "server": {
    "host": "0.0.0.0",
    "port": 8787
  },
  "providers": {
    "default_provider_id": "wandb_inf",
    "items": [
      {
        "api_key": "your-api-key",
        "base_url": "https://api.inference.wandb.ai/v1",
        "enabled": true,
        "id": "wandb_inf",
        "model": "Qwen/Qwen3-235B-A22B-Thinking-2507",
        "name": "wandb",
        "temperature": 0.2,
        "timeout_seconds": 300,
        "type": "openai_compatible",
        "verify_tls": true
      }
    ]
  }
}' > custom_config.json

# Run with custom config
docker run -d \
  --name miniclaw \
  -p 8787:8787 \
  -v $(pwd)/custom_config.json:/home/miniclaw/.miniclaw/miniclaw_config.json \
  -v miniclaw_data:/home/miniclaw/.miniclaw \
  miniclaw
```

### 5. Telegram Integration in Docker

To enable Telegram integration, you'll need to configure the bot token in your config file or environment variables:

```yaml
# In docker-compose.yml
services:
  miniclaw:
    # ... other configuration
    environment:
      - MINICLAW_HOST=0.0.0.0
      - MINICLAW_PORT=8787
      - TELEGRAM_BOT_TOKEN=your-bot-token-here
    volumes:
      - miniclaw_data:/home/miniclaw/.miniclaw
```

Or update the config file directly:

```json
{
  "telegram": {
    "enabled": true,
    "bot_token": "your-bot-token-here",
    "allowed_chat_ids": [],
    "binding_mode": "single",
    "poll_interval_seconds": 2,
    "pairing_required": true,
    "pairing_code_ttl_seconds": 600,
    "progress_update_seconds": 12
  }
}
```

## Persistent Data

The Docker setup uses a named volume (`miniclaw_data`) to persist data across container restarts. This includes:

- Configuration files
- Skills
- Memory files
- Job definitions
- Plugin configurations

To backup persistent data:

```bash
# Create backup
docker run --rm -v miniclaw_data:/source -v $(pwd):/backup \
  alpine tar czf /backup/miniclaw_backup.tar.gz -C /source .

# Restore from backup
docker run --rm -v miniclaw_data:/target -v $(pwd):/backup \
  alpine tar xzf /backup/miniclaw_backup.tar.gz -C /target
```

## Updating MiniClaw in Docker

To update MiniClaw:

```bash
# Pull latest changes
git pull origin dev

# Rebuild the image
docker build -t miniclaw .

# Stop and remove the current container
docker stop miniclaw
docker rm miniclaw

# Start a new container
docker run -d \
  --name miniclaw \
  -p 8787:8787 \
  -v miniclaw_data:/home/miniclaw/.miniclaw \
  miniclaw
```

Or with Docker Compose:

```bash
# Pull latest changes
git pull origin dev

# Rebuild and restart
docker-compose up -d --build
```

## Monitoring Docker Deployments

### Check Container Logs

```bash
# Docker
docker logs miniclaw

# Docker Compose
docker-compose logs miniclaw

# Follow logs
docker logs -f miniclaw
```

### Access Container Shell

```bash
# Docker
docker exec -it miniclaw /bin/bash

# Docker Compose
docker-compose exec miniclaw /bin/bash
```

### Health Checks

The Docker images include built-in health checks. You can also manually check:

```bash
# Check if service is responding
curl -f http://localhost:8787/api/health

# Check container health status
docker inspect --format='{{json .State.Health}}' miniclaw
```

## Docker Security Best Practices

### 1. Run as Non-Root User

The provided Dockerfile already runs as a non-root user (`miniclaw`), which is a security best practice.

### 2. Read-Only Filesystem

The Docker Compose example includes `read_only: true` which prevents the container from writing to most of the filesystem.

### 3. Resource Limits

Set appropriate resource limits to prevent resource exhaustion:

```yaml
deploy:
  resources:
    limits:
      memory: 1G
      cpus: '0.5'
```

### 4. Network Security

Only expose necessary ports and consider using Docker networks for internal communication:

```yaml
services:
  miniclaw:
    # ... other config
    networks:
      - miniclaw-net
    expose:
      - "8787"  # Only expose internally

networks:
  miniclaw-net:
    driver: bridge
```

## Troubleshooting Docker Deployments

### Common Issues

1. **Port Already in Use**: Change the host port mapping:
   ```bash
   docker run -d --name miniclaw -p 8788:8787 miniclaw
   ```

2. **Permission Issues**: Ensure the Docker user has proper permissions to access volumes.

3. **Configuration Errors**: Validate your config file JSON syntax before mounting it.

4. **Health Check Failures**: Check container logs for startup errors:
   ```bash
   docker logs miniclaw
   ```

### Volume Issues

If persistent data seems corrupted:

```bash
# Check volume contents
docker volume inspect miniclaw_data

# Create a new volume and migrate data if needed
docker volume create miniclaw_data_new
```

## Docker Multi-Stage Builds (Advanced)

For production deployments that require minimal image size:

```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app
COPY . .

# Install build dependencies and compile
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --upgrade pip \
    && pip install --no-cache-dir -e .

# Production stage
FROM python:3.11-slim

# Set environment variables
ENV MINICLAW_HOST=0.0.0.0
ENV MINICLAW_PORT=8787
ENV MINICLAW_WORKSPACE=/home/miniclaw/.miniclaw
ENV PATH="/home/miniclaw/.local/bin:${PATH}"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash miniclaw

USER miniclaw
WORKDIR /home/miniclaw

# Copy only the installed packages and source code
COPY --from=builder --chown=miniclaw:miniclaw /usr/local /usr/local
COPY --from=builder --chown=miniclaw:miniclaw /home/miniclaw/miniclaw /home/miniclaw/miniclaw

WORKDIR /home/miniclaw/miniclaw

# Create workspace directory
RUN mkdir -p /home/miniclaw/.miniclaw

# Expose the default port
EXPOSE 8787

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8787/api/health || exit 1

# Run MiniClaw server
CMD ["python", "-c", "from miniclaw import run; run()"]
```

This enhanced deployment guide provides comprehensive instructions for deploying MiniClaw in Docker containers, covering everything from basic setup to advanced production configurations.

## Security Hardening

### 1. User Permissions

```bash
# Create dedicated service user
sudo useradd -r -s /bin/false miniclaw

# Set proper ownership
sudo chown -R miniclaw:miniclaw ~/.miniclaw
sudo chmod 700 ~/.miniclaw
```

### 2. Network Security

Configure firewall to restrict access:

```bash
# UFW example
sudo ufw allow from 10.0.0.0/8 to any port 8787
sudo ufw allow from 172.16.0.0/12 to any port 8787
sudo ufw allow from 192.168.0.0/16 to any port 8787
```

### 3. Reverse Proxy Configuration

Nginx configuration with SSL:

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    location / {
        proxy_pass http://127.0.0.1:8787;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout settings
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

## Production Configuration

Create a hardened configuration file:

```json
{
  "server": {
    "host": "127.0.0.1",
    "port": 8787
  },
  "providers": {
    "default_provider_id": "your_provider",
    "items": [
      {
        "id": "your_provider",
        "name": "Production Provider",
        "type": "ollama",
        "enabled": true,
        "base_url": "http://your-model-server:11434",
        "api_key": "your-api-key",
        "model": "your-model-name",
        "temperature": 0.2,
        "timeout_seconds": 300,
        "verify_tls": true,
        "system_prompt_override": ""
      }
    ]
  },
  "telegram": {
    "enabled": true,
    "bot_token": "your-telegram-token",
    "allowed_chat_ids": ["your-chat-id"],
    "binding_mode": "single",
    "poll_interval_seconds": 2,
    "pairing_required": true,
    "pairing_code_ttl_seconds": 300,
    "progress_update_seconds": 12
  },
  "tools": {
    "enabled": true,
    "max_steps": 4,
    "allow_shell": false,
    "allow_filesystem": true,
    "allow_network": true,
    "allow_browser": true,
    "allow_mcp": true,
    "command_timeout_seconds": 25,
    "output_char_limit": 12000,
    "working_directory": "/home/miniclaw/.miniclaw/workspace"
  },
  "monitoring": {
    "max_events": 10000
  }
}
```

## Process Management

### Systemd Service

Create `/etc/systemd/system/miniclaw.service`:

```ini
[Unit]
Description=MiniClaw AI Agent
After=network.target

[Service]
Type=simple
User=miniclaw
Group=miniclaw
WorkingDirectory=/home/miniclaw/miniclaw
Environment=PATH=/home/miniclaw/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/home/miniclaw/.local/bin/miniclaw gateway
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/miniclaw/.miniclaw

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable miniclaw
sudo systemctl start miniclaw
sudo systemctl status miniclaw
```

## Monitoring and Logging

### Log Rotation

Create `/etc/logrotate.d/miniclaw`:

```
/home/miniclaw/.miniclaw/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 640 miniclaw miniclaw
    sharedscripts
    postrotate
        systemctl reload miniclaw
    endscript
}
```

### Health Checks

Monitor the health endpoint:

```bash
#!/bin/bash
# health_check.sh
HEALTH_URL="http://localhost:8787/api/health"
TIMEOUT=10

if curl -sf --max-time $TIMEOUT $HEALTH_URL > /dev/null; then
    echo "Healthy"
    exit 0
else
    echo "Unhealthy"
    exit 1
fi
```

## Backup and Recovery

### Regular Backups

```bash
#!/bin/bash
# backup_miniclaw.sh
BACKUP_DIR="/backup/miniclaw"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR/$DATE
tar -czf $BACKUP_DIR/$DATE/miniclaw_backup.tar.gz \
    -C /home/miniclaw/.miniclaw .

# Keep only last 30 days
find $BACKUP_DIR -type d -mtime +30 -exec rm -rf {} \;
```

Schedule with cron:

```bash
# Daily backup at 2 AM
0 2 * * * /home/miniclaw/scripts/backup_miniclaw.sh
```

## Scaling Considerations

### Horizontal Scaling

For high-traffic deployments, consider:

1. **Load Balancer**: Distribute requests across multiple instances
2. **Shared Storage**: Use NFS or cloud storage for shared workspace
3. **Database**: Replace file-based storage with PostgreSQL for state
4. **Caching**: Implement Redis for frequently accessed data

### Resource Limits

Set appropriate resource limits in systemd:

```ini
[Service]
# Memory limit
MemoryLimit=1G

# CPU quota
CPUQuota=50%

# File descriptor limits
LimitNOFILE=65536

# Process limits
LimitNPROC=1024
```

## Troubleshooting

### Common Issues

1. **Port conflicts**:
   ```bash
   sudo netstat -tlnp | grep :8787
   ```

2. **Permission errors**:
   ```bash
   sudo chown -R miniclaw:miniclaw /home/miniclaw/.miniclaw
   ```

3. **Service won't start**:
   ```bash
   sudo journalctl -u miniclaw -f
   ```

### Logs

Check systemd logs:
```bash
sudo journalctl -u miniclaw
sudo journalctl -u miniclaw --since "1 hour ago"
```

Check application logs:
```bash
tail -f /home/miniclaw/.miniclaw/logs/miniclaw.log
```

## Updates and Maintenance

### Updating MiniClaw

```bash
# Stop service
sudo systemctl stop miniclaw

# Backup current installation
sudo cp -r /home/miniclaw/miniclaw /home/miniclaw/miniclaw.backup

# Update code
cd /home/miniclaw/miniclaw
git pull

# Update dependencies
pip install -e .

# Start service
sudo systemctl start miniclaw
```

### Security Updates

Regularly update system packages:
```bash
sudo apt update && sudo apt upgrade -y
```

Monitor security advisories for dependencies:
```bash
pip list --outdated
```

## Disaster Recovery

### Restore from Backup

```bash
# Stop service
sudo systemctl stop miniclaw

# Restore from backup
BACKUP_FILE="/backup/miniclaw/20231201_020000/miniclaw_backup.tar.gz"
tar -xzf $BACKUP_FILE -C /home/miniclaw/.miniclaw

# Fix permissions
sudo chown -R miniclaw:miniclaw /home/miniclaw/.miniclaw

# Start service
sudo systemctl start miniclaw
```

This deployment guide provides a solid foundation for running MiniClaw in production environments with appropriate security and reliability measures.