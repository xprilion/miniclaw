# MiniClaw

MiniClaw is a secure, minimal AI agent infrastructure built for production environments. Inspired by OpenClaw, it provides a lightweight yet powerful platform for running AI agents locally with enterprise-grade features.

Configuration and data are stored in `~/.miniclaw`, while this repository contains only the core code.

[![Build](https://github.com/xprilion/miniclaw/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/xprilion/miniclaw/actions/workflows/ci.yml)

## Key Features

### Security
- Advanced sandboxing with path validation
- Permission controls and rate limiting
- Content filtering and input sanitization

### Production Ready
- Comprehensive monitoring and error handling
- Scalable architecture with CI/CD integration
- Detailed event logging and tracking

### Developer Friendly
- Extensible plugin system with lifecycle hooks
- Rich API and comprehensive testing
- Well-documented architecture

### User Experience
- Interactive setup wizard
- Modern web interface with dark/light mode
- Multiple AI provider support (Ollama, OpenAI, OpenRouter, etc.)

## Installation

From source (recommended):
```bash
git clone https://github.com/xprilion/miniclaw.git
cd miniclaw
uv pip install -e .
miniclaw install
```

With uv (if published):
```bash
uv tool install miniclaw
miniclaw setup
```

The installation process includes optional KeyDB installation for job execution support.

## Quick Start

1. Initialize (creates `~/.miniclaw` with config, memory, skills, plugins)
   ```bash
   miniclaw install
   ```
   Or use the simplified command: `miniclaw install`

2. Configure by editing `~/.miniclaw/miniclaw_config.json`

3. Start the server
   ```bash
   miniclaw gateway
   ```

4. Chat via CLI or web UI
   ```bash
   miniclaw agent -m "What is 2+2?"
   ```
   Or visit http://127.0.0.1:8787

## Running as a Service

To run MiniClaw as a background service that automatically starts on boot:

```bash
python -m miniclaw.service_installer
```

This will detect your operating system and create the appropriate service configuration files. Follow the on-screen instructions to complete the installation.

See [SERVICE_INSTALLATION.md](SERVICE_INSTALLATION.md) for detailed instructions for each platform.

## Available Commands

### Core Commands
- `install` - Create workspace and guide through prerequisites with interactive setup
- `uninstall [--yes]` - Remove workspace directory
- `gateway [--host HOST] [--port PORT]` - Start the server (web + Telegram)
- `gateway start` - Start MiniClaw as a background service
- `gateway stop` - Stop the MiniClaw service
- `gateway restart` - Restart the MiniClaw service
- `gateway status` - Check the status of the MiniClaw service
- `doctor` - Check Python, workspace, config, Ollama, server
- `status` - Show system status (alias for doctor)
- `update` - Update dependencies and existing installation
- `health` - Check /api/health

### Agent Interaction
- `agent [-m MESSAGE] [MESSAGE_POS] [--provider PROVIDER] [--json] [--stdin]` - Chat with the agent
- `chat [MESSAGE] [--source SOURCE] [--provider PROVIDER] [--stdin] [--json]` - Send chat message
- `history [--limit LIMIT]` - Get chat history

### Configuration
- `config get` - Get normalized config JSON
- `config set --file FILE` - PUT config JSON from file
- `config raw-get` - Get raw config text
- `config raw-set [--file FILE] [--stdin]` - PUT raw config text from file or stdin

### AI Providers (miniclaw providers)
- `providers list` - List configured model providers
- `providers default --id ID` - Set default provider
- `providers delete --id ID` - Delete provider
- `providers save --id ID --name NAME --type TYPE --base-url URL --model MODEL [--temperature TEMP] [--timeout TIMEOUT] [--api-key KEY] [--prompt-override PROMPT] [--disable] [--no-verify-tls]` - Create or update provider

### Memory Management (miniclaw memory)
- `memory list` - List memory files and content
- `memory get --name NAME` - Read one memory file
- `memory save --name NAME [--file FILE] [--stdin]` - Save a memory file

### Skills
- `skills` - List skills
- `skill-save --id ID [--file FILE] [--stdin]` - Save markdown skill file
- `skill-delete --id ID` - Delete markdown skill file

### Jobs (miniclaw jobs)
- `jobs status` - Get jobs status
- `jobs save --id ID --name NAME --prompt PROMPT [--interval INTERVAL] [--disabled] [--telegram-chat-id ID]` - Create or update job
- `jobs delete --id ID` - Delete job
- `jobs run --id ID` - Trigger job now

### Telegram Integration
- `telegram restart` - Restart Telegram poller
- `telegram test --chat-id CHAT_ID [--message MESSAGE]` - Send Telegram test message
- `telegram pairings` - Get pairing status and requests
- `telegram pair-start [--ttl TTL]` - Create Telegram pairing code
- `telegram pair-confirm --request-id REQUEST_ID` - Confirm pairing request
- `telegram pair-reject --request-id REQUEST_ID` - Reject pairing request
- `telegram unbind` - Remove currently bound Telegram chat

### Service Management
- `service install` - Install MiniClaw as a system service
- `service uninstall` - Uninstall the MiniClaw service
- `service start` - Start the MiniClaw service
- `service stop` - Stop the MiniClaw service
- `service restart` - Restart the MiniClaw service
- `service status` - Check the status of the MiniClaw service
- `models [--provider PROVIDER]` - List provider models
- `usage [--limit LIMIT]` - Get token usage summary
- `runtime` - Get runtime snapshot
- `events [--since-id SINCE_ID] [--limit LIMIT]` - Get monitoring events
- `plugins list` - List plugins
- `plugins reload` - Reload plugins

## Documentation

- [Getting Started Guide](docs/getting_started.md)
- [Setup Guide](docs/setup.md)
- [Architecture Overview](docs/architecture.md)
- [Production Deployment](docs/deployment.md)
- [API Documentation](docs/api.md)
- [CLI Documentation](docs/cli.md)
- [CLI Styling Guide](docs/cli_styling.md)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.