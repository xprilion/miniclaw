# MiniClaw

MiniClaw is a Telegram-first AI coding agent that runs locally in your terminal, works inside a project directory, and takes user instructions from a paired Telegram bot instead of the CLI itself.

Configuration and data are stored in `~/.miniclaw`, while this repository contains only the core code.

[![Build](https://github.com/xprilion/miniclaw/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/xprilion/miniclaw/actions/workflows/ci.yml)

[![Code Quality](https://github.com/xprilion/miniclaw/actions/workflows/qodana_code_quality.yml/badge.svg)](https://github.com/xprilion/miniclaw/actions/workflows/qodana_code_quality.yml)

## Key Features

### Coding First
- Focused on code changes, repo inspection, shell workflows, and local debugging
- Project workspace tools for reading files, writing files, and running commands
- Telegram-native approval flow for sensitive actions like shell commands and file writes

### Telegram Native
- Pair a single Telegram chat to control the agent remotely
- Progress updates and permission prompts are delivered in Telegram
- Typing heartbeats keep long-running tasks feeling responsive

### Local Monitoring
- The terminal is for onboarding, monitoring, and service control
- Event and runtime commands show what the agent is doing locally
- Clean separation between remote control and local observability

### Flexible Models
- Multiple AI provider support (Ollama, OpenAI-compatible APIs, OpenRouter, LiteLLM)
- Plugin and MCP integration for extending the coding workflow
- Persistent memory, history, and monitoring event logs

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

The installation process includes optional database installation (Valkey, KeyDB, or Redis) for job execution support.

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

4. Pair Telegram
   ```bash
   Send any message to your Telegram bot
   miniclaw telegram pair-claim --code <CODE>
   ```

5. Send coding instructions from the paired Telegram chat and monitor locally with:
   ```bash
   miniclaw events
   miniclaw runtime
   ```

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
- `gateway [--host HOST] [--port PORT]` - Start the Telegram coding-agent bridge and monitor services
- `gateway start` - Start MiniClaw as a background service
- `gateway stop` - Stop the MiniClaw service
- `gateway restart` - Restart the MiniClaw service
- `gateway status` - Check the status of the MiniClaw service
- `doctor` - Check Python, workspace, config, Ollama, server
- `status` - Show system status (alias for doctor)
- `update` - Update dependencies and existing installation
- `health` - Check /api/health

### Telegram & Monitoring
- `telegram pair-claim --code CODE` - Approve a Telegram pairing request by claim code
- `telegram pair-start [--ttl TTL]` - Create Telegram pairing code
- `telegram pairings` - Get pairing status and requests
- `telegram pair-confirm --request-id REQUEST_ID` - Confirm pairing request
- `telegram pair-reject --request-id REQUEST_ID` - Reject pairing request
- `telegram unbind` - Remove currently bound Telegram chat
- `history [--limit LIMIT]` - Get chat history
- `events [--since-id SINCE_ID] [--limit LIMIT]` - Get monitoring events
- `runtime` - Get runtime snapshot

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

### Deprecated Local Chat Commands
- `agent ...` - Local interactive chat is disabled; send instructions through Telegram instead
- `chat ...` - Local interactive chat is disabled; send instructions through Telegram instead

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
