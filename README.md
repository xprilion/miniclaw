# MiniClaw

MiniClaw is a production-ready, secure, and minimal AI agent infrastructure inspired by OpenClaw. Originally designed as a minimal local agent optimized for smaller models, MiniClaw has been enhanced with enterprise-grade features while maintaining its lightweight nature and ease of use.

Config and data live in **`~/.miniclaw`**; this repo contains only code.

## Key Features

### 🛡️ Enhanced Security
- **Advanced Sandboxing**: Path validation and command filtering
- **Permission Controls**: Fine-grained access management
- **Rate Limiting**: User and IP-based rate limiting
- **Content Filtering**: Automatic redaction of sensitive information
- **Input Sanitization**: Protection against injection attacks

### 🚀 Production Ready
- **Comprehensive Monitoring**: Detailed event logging and tracking
- **Error Handling**: Robust error recovery and reporting
- **Scalable Architecture**: Designed for production deployment
- **CI/CD Integration**: Automated testing and deployment pipelines

### 👩‍💻 Developer Friendly
- **Extensible Plugin System**: Lifecycle hooks and execution contexts
- **Comprehensive Testing**: Full test suite with CI/CD integration
- **Rich API**: RESTful API for all operations
- **Detailed Documentation**: Architecture docs and examples

### 🌟 User Experience
- **Interactive Setup Wizard**: Guided installation for non-developers
- **Modern Web Interface**: Responsive UI with dark/light mode
- **Enhanced Monitoring Dashboard**: Visual insights into system performance
- **Multiple Provider Support**: Ollama, OpenAI, OpenRouter, and more

## Install

**From source (recommended)**

```bash
git clone <repo>
cd miniclaw
uv pip install -e .   # or: pip install -e .
miniclaw setup        # Interactive setup wizard
```

**With uv (if published)**

```bash
uv tool install miniclaw
miniclaw setup
```

## Quick Start

1. **Initialize** (creates `~/.miniclaw` with config, memory, skills, plugins)

   ```bash
   miniclaw setup  # Interactive setup wizard (recommended for new users)
   # OR
   miniclaw install  # Manual setup
   ```

2. **Configure** — Edit `~/.miniclaw/miniclaw_config.json` (Ollama URL, Telegram token, etc.).

3. **Start the server** (web + Telegram)

   ```bash
   miniclaw gateway
   ```

4. **Chat**

   ```bash
   miniclaw agent -m "What is 2+2?"
   ```

   Or open http://127.0.0.1:8787 and use the web UI.

5. **Check status**

   ```bash
   miniclaw status
   ```

## CLI Reference

| Command | Description |
|---------|-------------|
| `miniclaw setup` | Run interactive setup wizard |
| `miniclaw onboard` | Initialize config & workspace (same as install) |
| `miniclaw install` | Create workspace and guide through prerequisites |
| `miniclaw agent -m "..."` | Chat with the agent |
| `miniclaw gateway` | Start the server (web + Telegram) |
| `miniclaw status` | Check Python, workspace, config, Ollama, server |
| `miniclaw chat "..."` | Send chat message (same as agent) |
| `miniclaw update` | Update dependencies |
| `miniclaw uninstall` | Remove workspace (`~/.miniclaw`) |

Use `miniclaw --help` for all commands (config, providers, skills, memory, telegram, scheduler, etc.).

## What It Includes

- Split web UI routes:
  - `/chat`
  - `/setup`
  - `/skills`
  - `/scheduler`
  - `/monitoring`
- Light/dark mode toggle.
- JSON config file (`miniclaw_config.json`) editable directly.
- Multi-provider model configuration (Ollama, OpenAI-compatible, LiteLLM, OpenRouter), with default provider and per-provider system prompt overrides.
- Channels setup flow in `/setup` (Telegram, WhatsApp/wacli placeholder, Email placeholder).
- Telegram bot integration with pairing-code authentication and single-chat binding.
- Telegram progress updates during longer tasks plus typing indicators while work is in progress.
- Built-in scheduler for recurring agent jobs.
- Skills as markdown files with UI CRUD.
- Default skill files and default scheduler jobs.
- Skill relevance matching (skills are guidance, not always-on prompt injection).
- Full monitoring events for prompts/actions/network/errors.
- Monitoring token usage totals by provider/model.
- Long-term memory files (`soul.md`, `user.md`, `project.md`, `journal.md`) with API + UI editing; agent reads memory into prompts and appends journal entries.
- CLI parity (`miniclaw_cli.py`) for core UI actions.
- **Enhanced Security**: Advanced sandboxing, permission controls, and input validation for safe tool execution.
- **Production Ready**: Deployment guides and security hardening recommendations.
- **Enhanced Plugin System**: New plugin architecture with lifecycle hooks and execution contexts.
- **Improved Setup**: Interactive wizard for easy configuration.

## Routes

- Landing: `/`
- Chat: `/chat`
- Setup: `/setup`
- Skills: `/skills`
- Scheduler: `/scheduler`
- Monitoring: `/monitoring`

## Enhanced Security Features

MiniClaw now includes comprehensive security mechanisms:

### Sandboxing
- File path validation to prevent access outside workspace
- Command filtering to block dangerous operations
- Input sanitization to prevent injection attacks

### Permission Controls
- Fine-grained tool access permissions
- User and group-based access control
- Feature flag management

### Rate Limiting
- User-based rate limiting
- IP-based rate limiting
- Configurable limits and windows

### Content Filtering
- Automatic redaction of sensitive information (API keys, passwords, etc.)
- Entropy-based secret detection
- Customizable filtering rules

## Enhanced Plugin System

The new plugin system provides:

### Lifecycle Management
- Load, enable, disable, and unload operations
- Lifecycle hooks (on_load, on_enable, on_disable, on_unload)
- Plugin-specific execution contexts

### Hook System
- Pre-prompt hooks for modifying agent prompts
- Post-response hooks for processing agent responses
- Message processing hooks
- Tool execution hooks
- Model response hooks

### Extensibility
- Rich plugin context with data storage
- Event logging integration
- Backward compatibility with existing plugins

## Enhanced Web Interface

### Modern Dashboard
- Visual monitoring and analytics
- Token usage tracking
- Event timeline visualization
- Performance metrics

### Improved Setup
- Tabbed configuration interface
- Provider testing capabilities
- Real-time validation
- Enhanced user experience

## Documentation

- [Getting Started Guide](docs/getting_started.md)
- [Architecture Overview](docs/architecture.md)
- [Production Deployment](docs/deployment.md)
- [Enhancement Summary](docs/enhancement_summary.md)
- [API Documentation](docs/api.md)

## Examples

- [Enhanced Features Demo](examples/enhanced_demo.py)
- [Example Plugin](plugins/example_enhanced_plugin.py)
- [Configuration Examples](miniclaw_config.example.json)

## Testing

Run the test suite:

```bash
python -m pytest tests/ -v
```

Or run all tests:

```bash
python tests/run_tests.py
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
