# MiniClaw Architecture

## Overview

MiniClaw is a Telegram-first AI coding agent. The terminal hosts the runtime, monitoring output, and service controls, while a paired Telegram bot is the primary place where the user sends instructions, receives progress updates, and approves sensitive actions.

## Core Components

### 1. Agent Engine
- **Core Agent**: Coding-focused intelligence layer that processes Telegram requests, utilizes skills, and executes tools
- **Skill System**: Markdown-based skill management for contextual guidance
- **Tool Runtime**: Secure execution environment for coding tools (shell, filesystem, network, browser, MCP)
- **Memory Store**: Persistent memory management with journaling and context retention

### 2. Model Integration
- **Multi-Provider Support**: Ollama, LiteLLM, OpenAI-compatible APIs, OpenRouter
- **Model Client**: Unified interface for interacting with different model providers
- **Prompt Engineering**: Advanced prompt construction with context, skills, and memory

### 3. Communication Layer
- **Telegram Integration**: Full-featured bot with pairing, progress updates, permission prompts, and single-chat binding
- **CLI Monitoring**: Local operator view for health, runtime, and event inspection
- **API Gateway**: RESTful API endpoints for all functionalities
- **Background Workers**: Long-running Telegram tasks execute off the polling loop so approvals can still be received in chat

### 4. Infrastructure
- **Configuration Management**: JSON-based config with environment variable overrides
- **Event Logging**: Comprehensive event tracking and monitoring
- **Jobs**: Recurring task execution with Telegram notifications
- **Plugin System**: Extensible architecture for custom functionality
- **MCP Integration**: Model Control Protocol support for external tools

### 5. Command Line Interface
- **Enhanced Styling**: Color-coded output with consistent design language
- **Interactive Navigation**: Telegram-first onboarding for bot setup and pairing
- **Monitoring Commands**: Runtime, event, history, and service inspection from the terminal
- **Helpful Error Messages**: Context-aware guidance when users try to interact locally instead of through Telegram

### 6. Security & Safety
- **Sandboxing**: Controlled execution environment for tools
- **Permission System**: Fine-grained access controls with Telegram-native approval prompts for sensitive actions
- **Input Validation**: Strict validation of all user inputs
- **Rate Limiting**: Protection against abuse and resource exhaustion

## Data Flow

1. **User Request**: Enters through the paired Telegram chat
2. **Preprocessing**: Plugins apply pre-prompt transformations
3. **Context Building**: Skills, memory, and history are integrated
4. **Model Interaction**: Prompt is sent to configured provider
5. **Tool Execution**: Coding tools are executed inside the configured project workspace
6. **Approval Flow**: Sensitive tool calls pause for Telegram approval when required
7. **Response Generation**: Final response is formatted and delivered back to Telegram
8. **Logging**: Events are recorded for local monitoring and debugging

## Safety Mechanisms

### Sandboxing
- Tools execute in restricted environments
- Filesystem access limited to designated directories
- Network requests filtered through allowlists
- Shell commands subject to strict validation

### Permission Controls
- Role-based access control (RBAC) for different user types
- Feature flags for enabling/disabling capabilities
- Per-tool permission grants with user confirmation
- Audit trail for all sensitive operations

### Input Validation
- Strict parsing and sanitization of all inputs
- Size limits on requests and responses
- Content filtering for potentially harmful instructions
- Rate limiting to prevent abuse

## Production Features

### Monitoring & Observability
- Real-time event streaming
- Token usage tracking by provider/model
- Performance metrics and latency tracking
- Error reporting with stack traces

### Reliability
- Graceful degradation during service outages
- Automatic retry mechanisms for transient failures
- Health checks and self-healing capabilities
- Backup and recovery procedures

### Scalability
- Horizontal scaling support for web interface
- Efficient resource utilization
- Caching mechanisms for frequently accessed data
- Load balancing considerations

## Extensibility

### Plugin Architecture
- Pre-prompt and post-response hooks
- Custom tool implementations
- UI extensions and modifications
- Integration with external systems

### Skill System
- Markdown-based skill definitions
- Keyword-based skill matching
- Dynamic skill loading and updating
- Community-contributed skill repository

## Deployment Options

### Local Development
- Single-process deployment
- SQLite for data storage
- Built-in web server
- Easy setup with minimal dependencies

### Production Deployment
- Containerized deployment with Docker
- PostgreSQL for data storage
- Reverse proxy (nginx) for SSL termination
- Process manager (systemd/supervisor) for reliability

### Cloud Deployment
- Kubernetes Helm charts
- Terraform configurations
- Auto-scaling groups
- Managed database services

## API Design

### RESTful Endpoints
- Consistent URL structure and HTTP methods
- Proper status codes and error responses
- JSON request/response bodies
- Authentication and authorization headers

### WebSocket Interface
- Real-time event streaming
- Bidirectional communication
- Message framing and protocol
- Connection management

## Configuration

### Environment Variables
- Runtime configuration through env vars
- Sensitive data through secure storage
- Provider-specific settings
- Feature flags and toggles

### Configuration Files
- JSON-based configuration
- Schema validation
- Default values and overrides
- Hot reloading capabilities

## Testing Strategy

### Unit Tests
- Component-level testing
- Mock-based isolation
- Coverage targets and metrics
- Continuous integration execution

### Integration Tests
- Cross-component interaction testing
- End-to-end scenario validation
- Provider compatibility testing
- Performance benchmarking

### Security Testing
- Penetration testing
- Vulnerability scanning
- Compliance verification
- Regular security audits

## Documentation

### User Guides
- Installation and setup instructions
- Configuration tutorials
- Usage examples and best practices
- Troubleshooting guides

### Developer Documentation
- Architecture diagrams and explanations
- API reference documentation
- Contribution guidelines
- Release process and versioning

### API Documentation
- Endpoint specifications
- Request/response schemas
- Authentication methods
- Rate limiting policies
