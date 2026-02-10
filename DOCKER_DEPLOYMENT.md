# MiniClaw Docker Deployment Guide

This guide explains how to deploy MiniClaw in a Docker container, which is the recommended way to run MiniClaw in production environments.

## Prerequisites

- Docker installed on your system
- Git (to clone the repository)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/xprilion/miniclaw.git
cd miniclaw
```

### 2. Build the Docker Image

```bash
docker build -t miniclaw .
```

### 3. Run MiniClaw Container

```bash
docker run -d \
  --name miniclaw \
  -p 8787:8787 \
  -v miniclaw_data:/home/miniclaw/.miniclaw \
  miniclaw
```

## Configuration

### Environment Variables

MiniClaw supports several environment variables for configuration:

```bash
docker run -d \
  --name miniclaw \
  -p 8787:8787 \
  -e MINICLAW_HOST=0.0.0.0 \
  -e MINICLAW_PORT=8787 \
  -e MINICLAW_WORKSPACE=/home/miniclaw/.miniclaw \
  -v miniclaw_data:/home/miniclaw/.miniclaw \
  miniclaw
```

### Custom Configuration

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

## Docker Compose Setup

For easier management, create a `docker-compose.yml` file:

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

volumes:
  miniclaw_data:
```

Then run:

```bash
docker-compose up -d
```

## Telegram Integration

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

## Updating MiniClaw

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

## Troubleshooting

### Check Container Logs

```bash
docker logs miniclaw
```

### Access Container Shell

```bash
docker exec -it miniclaw /bin/bash
```

### Common Issues

1. **Port Already in Use**: Change the host port mapping:
   ```bash
   docker run -d --name miniclaw -p 8788:8787 miniclaw
   ```

2. **Permission Issues**: Ensure the Docker user has proper permissions to access volumes.

3. **Configuration Errors**: Validate your config file JSON syntax before mounting it.

## Advanced Configuration

### Custom Dockerfile

For custom requirements, create a custom Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash miniclaw

USER miniclaw
WORKDIR /home/miniclaw

# Clone and install MiniClaw
RUN git clone https://github.com/xprilion/miniclaw.git
WORKDIR /home/miniclaw/miniclaw
RUN pip install --no-cache-dir -e .

# Expose port
EXPOSE 8787

# Run MiniClaw
CMD ["python", "-c", "from miniclaw import run; run()"]
```

### Health Checks

Add health checks to your Docker Compose file:

```yaml
services:
  miniclaw:
    # ... other configuration
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8787/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
```

This Docker deployment guide provides a comprehensive approach to running MiniClaw in containerized environments, ensuring consistency across different deployment targets.