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

Create a Dockerfile:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . .

RUN pip install -e .

EXPOSE 8787

USER 1000
CMD ["miniclaw", "gateway"]
```

Build and run:

```bash
docker build -t miniclaw .
docker run -d -p 8787:8787 --name miniclaw \
  -v ~/.miniclaw:/home/miniclaw/.miniclaw \
  miniclaw
```

### 3. Docker Compose (Recommended)

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  miniclaw:
    build: .
    ports:
      - "8787:8787"
    volumes:
      - miniclaw_data:/home/miniclaw/.miniclaw
    environment:
      - MINICLAW_HOST=0.0.0.0
      - MINICLAW_PORT=8787
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

volumes:
  miniclaw_data:
```

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