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