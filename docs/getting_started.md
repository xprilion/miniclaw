# Getting Started with MiniClaw

MiniClaw is a lightweight, production-ready AI agent infrastructure that's easy to set up and use for both developers and non-developers.

## Quick Setup (Non-Developers)

If you're not a developer, use the interactive setup wizard:

```bash
# Clone the repository
git clone <repo-url>
cd miniclaw

# Install dependencies
pip install -e .

# Run the setup wizard
miniclaw setup
```

The wizard will guide you through:
1. Checking system requirements
2. Setting up your workspace
3. Configuring an AI model provider
4. Setting up Telegram integration (optional)
5. Creating default configuration files

## For Developers

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd miniclaw

# Install with pip
pip install -e .

# Or with uv (faster)
uv pip install -e .
```

### Manual Setup

1. **Initialize workspace**:
   ```bash
   miniclaw install
   ```

2. **Configure AI model**:
   Edit `~/.miniclaw/miniclaw_config.json` to set up your preferred model provider:
   - **Ollama** (local, free): Set up Ollama and use local models
   - **OpenAI API**: Use GPT models with your API key
   - **OpenRouter**: Access various models through one API

3. **Start the server**:
   ```bash
   miniclaw gateway
   ```

4. **Use the web interface**:
   Open http://127.0.0.1:8787 in your browser

5. **Or chat via CLI**:
   ```bash
   miniclaw agent -m "Hello, what can you help me with?"
   ```

## Key Features

### Web Interface
- Chat with your AI agent
- Configure settings through UI
- Manage skills and memory
- Monitor system status

### Telegram Integration
- Interact with MiniClaw through Telegram
- Receive progress updates during long tasks
- Secure pairing mechanism

### Skills System
- Contextual guidance through markdown files
- Automatic skill matching based on your queries
- Easy to create and manage custom skills

### Tool Execution
- Safe execution of system commands
- File system operations (read/write/list)
- Web browsing and URL fetching
- Integration with external tools via MCP

### Memory Management
- Persistent context through memory files
- Automatic journaling of interactions
- Customizable memory structure

## Security Features

MiniClaw includes several built-in security mechanisms:

- **Sandboxing**: Tools execute in restricted environments
- **Path validation**: File operations limited to workspace
- **Command validation**: Dangerous commands are blocked
- **Input sanitization**: Protection against injection attacks
- **Rate limiting**: Prevention of abuse
- **Permission controls**: Fine-grained access management

## Configuration

The main configuration file is located at `~/.miniclaw/miniclaw_config.json`. Key sections include:

- **providers**: AI model provider settings
- **tools**: Tool execution permissions and limits
- **telegram**: Telegram bot configuration
- **memory**: Memory file settings
- **scheduler**: Automated task scheduling

## Next Steps

After setup, try these commands:

```bash
# Check system status
miniclaw status

# Chat with the agent
miniclaw agent -m "What can you help me with?"

# List available skills
miniclaw skills

# Check token usage
miniclaw usage
```

For more detailed information, see the [full documentation](./architecture.md).