# MiniClaw CLI Documentation

The MiniClaw CLI provides a comprehensive set of commands for managing your AI agent infrastructure. All commands feature colorful, styled output with consistent design principles and enhanced user experience.

## Table of Contents

- [Installation and Setup](#installation-and-setup)
- [Core Commands](#core-commands)
- [System Management](#system-management)
- [AI Provider Management](#ai-provider-management)
- [Content Management](#content-management)
- [Communication Channels](#communication-channels)
- [Job Scheduling](#job-scheduling)
- [Monitoring and Diagnostics](#monitoring-and-diagnostics)

## Installation and Setup

### `miniclaw install`

Run the enhanced interactive setup wizard with Valkey installation.

```bash
miniclaw install
```

Features:
- Step-by-step interactive setup process
- Valkey automatic installation and configuration
- Navigation between steps (back, forward, jump to specific steps)
- Configuration review before applying changes
- Workspace customization options
- Multiple AI provider support (Ollama, OpenAI, OpenRouter)
- Optional Telegram bot setup

### `miniclaw onboard`

Alias for `miniclaw install`.

```bash
miniclaw onboard
```

## Core Commands

### `miniclaw agent`

Chat with the agent using styled output.

```bash
miniclaw agent -m "What is 2+2?"
miniclaw agent "Explain quantum computing"
echo "Summarize this" | miniclaw agent --stdin
```

Options:
- `-m, --message MESSAGE`: Chat message
- `--stdin`: Read message from stdin
- `--json`: Output raw JSON response
- `--provider PROVIDER`: Specify provider ID

### `miniclaw chat`

Send chat messages with styled responses.

```bash
miniclaw chat "What's the weather like?"
miniclaw chat --source web "Tell me a joke"
```

Options:
- `-m, --message MESSAGE`: Chat message
- `--stdin`: Read message from stdin
- `--json`: Output raw JSON response
- `--source SOURCE`: Message source (default: cli)
- `--provider PROVIDER`: Specify provider ID

### `miniclaw gateway`

Start the MiniClaw server with startup feedback.

```bash
miniclaw gateway
miniclaw gateway --host 0.0.0.0 --port 8080
```

Options:
- `--host HOST`: Bind host (default: 127.0.0.1)
- `--port PORT`: Bind port (default: 8787)

## System Management

### `miniclaw status`

Check system status with color-coded results.

```bash
miniclaw status
```

Displays:
- Python environment information
- Workspace status
- Configuration file status
- AI provider connectivity
- Server status

### `miniclaw doctor`

Comprehensive system diagnostics.

```bash
miniclaw doctor
```

Performs detailed checks including:
- Python version verification
- Workspace integrity
- Configuration validation
- Provider connectivity
- Server health

### `miniclaw update`

Update dependencies with progress indicators.

```bash
miniclaw update
```

Features:
- Automatic dependency updates using uv or pip
- Configuration defaults refresh
- Progress feedback during updates
- Success/failure indicators

### `miniclaw uninstall`

Remove workspace with confirmation and preview.

```bash
miniclaw uninstall
miniclaw uninstall --yes  # Skip confirmation
```

Options:
- `--yes, -y`: Skip confirmation prompt

## AI Provider Management

### `miniclaw providers`

Manage AI providers.

```bash
miniclaw providers list
miniclaw providers default --id ollama_default
miniclaw providers delete --id openai_fallback
```

Subcommands:
- `list`: List configured providers
- `default --id ID`: Set default provider
- `delete --id ID`: Delete a provider
- `save`: Create or update a provider

### `miniclaw providers save`

Create or update an AI provider configuration.

```bash
miniclaw providers save \
  --id openai_gpt4 \
  --name "OpenAI GPT-4" \
  --type openai_compatible \
  --base-url https://api.openai.com/v1 \
  --api-key sk-your-api-key \
  --model gpt-4-turbo \
  --temperature 0.7
```

Options:
- `--id ID`: Provider ID (required)
- `--name NAME`: Provider name (required)
- `--type TYPE`: Provider type (ollama, openai_compatible, openrouter, litellm)
- `--base-url URL`: Base URL for API
- `--api-key KEY`: API key for authentication
- `--model MODEL`: Default model name
- `--temperature TEMP`: Temperature setting (0.0-2.0)
- `--timeout SECONDS`: Request timeout
- `--prompt-override TEXT`: Override system prompt
- `--disable`: Disable provider
- `--no-verify-tls`: Disable TLS verification

## Content Management

### `miniclaw skills`

Manage skill files with CRUD operations.

```bash
miniclaw skills
miniclaw skills --json  # Raw JSON output
```

### `miniclaw skills save`

Create or update a skill file.

```bash
miniclaw skills save --id research_helper --file ./research_skill.md
echo "# Research Helper\nkeywords: research, analysis\n\nHelp with research tasks." | miniclaw skills save --id research_helper --stdin
```

Options:
- `--id ID`: Skill ID (required)
- `--file FILE`: Read content from file
- `--stdin`: Read content from stdin

### `miniclaw skills delete`

Delete a skill file.

```bash
miniclaw skills delete --id research_helper
```

Options:
- `--id ID`: Skill ID to delete (required)

### `miniclaw memory`

Manage memory files.

```bash
miniclaw memory list
miniclaw memory get --name soul.md
```

Subcommands:
- `list`: List memory files
- `get --name NAME`: Get memory file content
- `save --name NAME`: Save memory file content

### `miniclaw memory save`

Save content to a memory file.

```bash
miniclaw memory save --name project.md --file ./project_notes.md
echo "# Project Notes\n\nKey decisions and constraints." | miniclaw memory save --name project.md --stdin
```

Options:
- `--name NAME`: Memory file name (required)
- `--file FILE`: Read content from file
- `--stdin`: Read content from stdin

## Communication Channels

### `miniclaw telegram`

Manage Telegram integration.

```bash
miniclaw telegram restart
miniclaw telegram test --chat-id 123456789 --message "Test message"
miniclaw telegram pairings
```

Subcommands:
- `restart`: Restart Telegram poller
- `test --chat-id ID --message MSG`: Send test message
- `pairings`: Get pairing status and requests
- `pair-start [--ttl SECONDS]`: Create pairing code
- `pair-confirm --request-id ID`: Confirm pairing request
- `pair-reject --request-id ID`: Reject pairing request
- `unbind`: Remove currently bound Telegram chat

## Job Scheduling

### `miniclaw jobs`

Manage scheduled jobs.

```bash
miniclaw jobs status
```

### `miniclaw jobs save`

Create or update a scheduled job.

```bash
miniclaw jobs save \
  --id daily_report \
  --name "Daily Report" \
  --prompt "Generate a daily summary of system activity" \
  --interval 86400 \
  --telegram-chat-id 123456789
```

Options:
- `--id ID`: Job ID (required)
- `--name NAME`: Job name (required)
- `--prompt PROMPT`: Agent prompt to run (required)
- `--interval SECONDS`: Run interval in seconds (min 10, default: 300)
- `--disabled`: Create job in disabled state
- `--telegram-chat-id ID`: Optional Telegram chat ID for job output

### `miniclaw jobs delete`

Delete a scheduled job.

```bash
miniclaw jobs delete --id daily_report
```

Options:
- `--id ID`: Job ID to delete (required)

### `miniclaw jobs run`

Trigger a job immediately.

```bash
miniclaw jobs run --id daily_report
```

Options:
- `--id ID`: Job ID to run (required)

## Monitoring and Diagnostics

### `miniclaw health`

Check server health status.

```bash
miniclaw health
```

### `miniclaw models`

List available AI models.

```bash
miniclaw models
miniclaw models --provider ollama_default
```

Options:
- `--provider PROVIDER`: Provider ID (default provider if omitted)

### `miniclaw usage`

Show token usage statistics.

```bash
miniclaw usage
miniclaw usage --limit 100
```

Options:
- `--limit LIMIT`: Max recent usage entries (default: 250)

### `miniclaw runtime`

Display runtime information.

```bash
miniclaw runtime
```

### `miniclaw history`

View chat history.

```bash
miniclaw history
miniclaw history --limit 50
```

Options:
- `--limit LIMIT`: Max history entries (default: 50)

### `miniclaw events`

Monitor system events.

```bash
miniclaw events
miniclaw events --since-id 100 --limit 100
```

Options:
- `--since-id ID`: Start from event ID (default: 0)
- `--limit LIMIT`: Max events to fetch (default: 100)

### `miniclaw config`

Manage configuration.

```bash
miniclaw config get
miniclaw config set --file ./new_config.json
miniclaw config raw-get
miniclaw config raw-set --file ./raw_config.json
```

Subcommands:
- `get`: Get current configuration
- `set --file FILE`: Update configuration from JSON file
- `raw-get`: Get raw configuration text
- `raw-set --file FILE`: Update raw configuration text

## CLI Styling and User Experience

All CLI commands feature enhanced user experience with:

### Color Coding
- **Green ✓**: Success operations
- **Red ✗**: Errors and failures
- **Yellow ⚠**: Warnings and cautions
- **Blue ℹ**: Informational messages
- **Purple**: Code snippets and technical terms

### Visual Hierarchy
- **Bold Headers**: Section titles and important information
- **Dimmed Text**: Secondary information and metadata
- **Structured Lists**: Organized content presentation
- **Progress Indicators**: Feedback during long operations

### Consistent Patterns
- **Step-by-step Navigation**: In setup and multi-stage operations
- **Confirmation Prompts**: For destructive operations
- **Helpful Error Messages**: With context and guidance
- **Standardized Output**: Consistent formatting across all commands

## Examples

### Complete Setup Workflow

```bash
# Install and configure MiniClaw
miniclaw install

# Check system status
miniclaw status

# Verify health
miniclaw health

# List available models
miniclaw models

# Start the server
miniclaw gateway
```

### Content Management Workflow

```bash
# List current skills
miniclaw skills

# Create a new skill
echo "# Code Review
keywords: code, review, programming

Provide code review feedback focusing on:
- Best practices
- Security considerations
- Performance optimizations" | miniclaw skills save --id code_review --stdin

# Update memory
echo "# Project Context
- Using Python 3.11+
- Deployed on cloud infrastructure
- CI/CD with GitHub Actions" | miniclaw memory save --name project.md --stdin

# Verify changes
miniclaw skills
miniclaw memory list
```

### Job Management Workflow

```bash
# Check current jobs
miniclaw jobs status

# Create a daily report job
miniclaw jobs save \
  --id daily_report \
  --name "Daily System Report" \
  --prompt "Generate a daily report summarizing system activity, token usage, and any errors from the past 24 hours." \
  --interval 86400

# Run immediately for testing
miniclaw jobs run --id daily_report

# Verify job status
miniclaw jobs status
```

### Monitoring Workflow

```bash
# Check system health
miniclaw health

# View recent events
miniclaw events --limit 20

# Check token usage
miniclaw usage --limit 10

# View chat history
miniclaw history --limit 10

# Get runtime information
miniclaw runtime
```