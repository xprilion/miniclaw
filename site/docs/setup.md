# MiniClaw Setup Guide

MiniClaw provides an enhanced interactive setup wizard that guides you through the complete installation process with step-by-step navigation and automatic dependency management.

## Enhanced Interactive Setup Wizard

The `miniclaw install` command launches a comprehensive setup wizard with the following features:

### Key Features

1. **Step-by-Step Navigation**
   - Progress through setup steps with clear indicators
   - Navigate backward to edit previous entries
   - Jump to specific steps as needed
   - Review and confirm configuration before applying

2. **Automatic Dependency Management**
   - Valkey installation and configuration
   - Ollama installation (if needed)
   - Package manager detection (uv/pip)
   - Service management (start/stop/status)

3. **Flexible Configuration Options**
   - Workspace customization
   - Multiple AI provider support
   - Optional Telegram integration
   - Default content creation

### Setup Steps

#### 1. Welcome Screen
Introduction to the setup process and overview of what will be configured.

#### 2. Prerequisites Check
Verification of system requirements:
- Python 3.9+ version check
- Package manager availability (uv or pip)
- Basic system compatibility

#### 3. Workspace Setup
Configuration of the MiniClaw workspace:
- Default location (`~/.miniclaw`)
- Custom workspace path option
- Directory structure creation
- Permission verification

#### 4. Model Provider Configuration
Selection and configuration of AI providers:
- **Ollama (Local)**: Run models locally on your machine
- **OpenAI API**: Use OpenAI's GPT models (requires API key)
- **OpenRouter**: Access to many models through one API (requires API key)

Each provider includes specific configuration options:
- API keys and authentication
- Model selection
- Endpoint URLs
- Performance settings

#### 5. Valkey Installation
Automatic Valkey installation and setup:
- Detection of existing Valkey/Redis installations
- Automatic installation for supported systems
- Service management configuration
- Python client installation

#### 6. Telegram Configuration
Optional Telegram bot setup:
- Bot token configuration
- Chat restrictions
- Pairing code settings
- Progress update intervals

#### 7. Review & Confirm
Configuration summary and verification:
- Complete settings overview
- Final confirmation before installation
- Option to edit any settings

#### 8. Installation
Execution of the setup process:
- Workspace directory creation
- Configuration file generation
- Default content creation
- Service initialization

### Valkey Integration

MiniClaw uses Valkey for job execution management. The setup wizard provides:

#### Automatic Installation
- Linux package manager integration (apt/yum)
- Direct download and installation
- Service daemon configuration
- Port and security settings

#### Service Management
- Automatic service startup
- Health check verification
- Connection string configuration
- Failover and redundancy options

#### Configuration Options
- Host and port settings
- Authentication and security
- Memory and performance tuning
- Backup and persistence

### AI Provider Configuration

#### Ollama (Local)
Setup for local model execution:
```bash
# During setup, you can choose to:
# 1. Use existing Ollama installation
# 2. Install Ollama automatically
# 3. Configure manually

# Default model pulled during setup:
# qwen3 (automatically downloaded)
```

Configuration options:
- Base URL (default: http://localhost:11434)
- Model selection
- Temperature settings
- Timeout configuration

#### OpenAI API
Cloud-based model access:
```bash
# Requires OpenAI API key
# Supports all OpenAI models
# Configurable endpoints
```

Configuration options:
- API key management
- Model selection (gpt-4, gpt-3.5-turbo, etc.)
- Base URL (api.openai.com/v1)
- Organization ID (optional)

#### OpenRouter
Multi-model provider access:
```bash
# Single API key for multiple models
# Access to Anthropic, Google, and other providers
# Competitive pricing
```

Configuration options:
- API key management
- Model routing
- Rate limit handling
- Provider fallback options

### Workspace Structure

The setup creates the following directory structure:

```
~/.miniclaw/
├── miniclaw_config.json    # Main configuration file
├── memory/                 # Long-term memory files
│   ├── soul.md            # Core agent personality
│   ├── user.md            # User profile and preferences
│   ├── project.md         # Project context and constraints
│   └── journal.md         # Activity log and history
├── skills/                 # Markdown skill files
│   ├── issue_triage.md    # Bug and issue handling
│   ├── research_compare.md # Comparison and evaluation
│   └── ship_plan.md       # Planning and execution
├── plugins/                # Custom plugin scripts
├── jobs/                   # Scheduled job configurations
└── generated_scripts/     # Auto-generated Python scripts
```

### Configuration Files

#### Main Configuration (miniclaw_config.json)
Generated during setup with provider-specific settings:

```json
{
  "server": {
    "host": "127.0.0.1",
    "port": 8787
  },
  "providers": {
    "default_provider_id": "ollama_default",
    "items": [
      {
        "id": "ollama_default",
        "name": "Ollama Default",
        "type": "ollama",
        "enabled": true,
        "base_url": "http://localhost:11434",
        "api_key": "",
        "model": "qwen3",
        "temperature": 0.2,
        "timeout_seconds": 300,
        "verify_tls": true,
        "system_prompt_override": ""
      }
    ]
  },
  "jobs": {
    "enabled": true,
    "jobs": [],
    "seeded_default_jobs": false
  }
}
```

### Post-Setup Configuration

After the initial setup, you can further customize your installation:

#### Adding Additional Providers
```bash
# Add OpenAI provider
miniclaw providers save \
  --id openai_gpt4 \
  --name "OpenAI GPT-4" \
  --type openai_compatible \
  --base-url https://api.openai.com/v1 \
  --api-key YOUR_API_KEY \
  --model gpt-4-turbo
```

#### Configuring Telegram
```bash
# Set up Telegram bot
miniclaw telegram pair-start
# Follow the pairing process in your Telegram app
```

#### Creating Custom Jobs
```bash
# Create a daily maintenance job
miniclaw jobs save \
  --id daily_maintenance \
  --name "Daily Maintenance" \
  --prompt "Perform daily system maintenance tasks and report status." \
  --interval 86400
```

### Troubleshooting

#### Common Issues

1. **Permission Denied Errors**
   ```bash
   # Solution: Run with appropriate permissions
   sudo miniclaw install
   # Or change workspace location
   MINICLAW_WORKSPACE=/path/to/writable/dir miniclaw install
   ```

2. **Port Conflicts**
   ```bash
   # Solution: Use different ports
   miniclaw gateway --port 8080
   # Or modify config file
   ```

3. **Valkey Installation Failures**
   ```bash
   # Solution: Install manually or use Redis
   # On Ubuntu:
   sudo apt install valkey-server
   # On macOS:
   brew install valkey
   ```

4. **Provider Connectivity Issues**
   ```bash
   # Solution: Verify API keys and endpoints
   miniclaw models --provider your_provider_id
   ```

#### Diagnostic Commands

```bash
# Check system status
miniclaw status

# Run comprehensive diagnostics
miniclaw doctor

# Verify health
miniclaw health

# Check configuration
miniclaw config get
```

### Advanced Configuration

#### Custom Workspace Location
```bash
# Set custom workspace during setup
MINICLAW_WORKSPACE=/custom/path miniclaw install

# Or modify existing installation
export MINICLAW_WORKSPACE=/custom/path
miniclaw status
```

#### Multiple Provider Setup
During the setup wizard, you can configure multiple providers and set priorities:

1. Primary provider (default)
2. Fallback providers
3. Specialized providers for specific tasks

#### Security Configuration
The setup wizard configures basic security settings:

- Sandbox path restrictions
- Command execution limits
- Rate limiting policies
- Content filtering rules

### Best Practices

1. **Regular Updates**
   ```bash
   # Keep dependencies current
   miniclaw update
   ```

2. **Backup Configuration**
   ```bash
   # Export configuration
   miniclaw config raw-get > backup_config.json
   ```

3. **Monitor Resource Usage**
   ```bash
   # Check token usage
   miniclaw usage
   # Monitor system events
   miniclaw events
   ```

4. **Secure API Keys**
   - Use environment variables for sensitive data
   - Regularly rotate API keys
   - Restrict key permissions when possible

### Unattended Setup

For automated deployments, you can prepare a configuration file and skip interactive setup:

```bash
# Create configuration file
echo '{"server":{"host":"127.0.0.1","port":8787},"providers":{...}}' > config.json

# Use existing configuration
miniclaw install --config config.json --non-interactive
```

Note: This advanced feature requires manual configuration file preparation.