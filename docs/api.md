# MiniClaw API Documentation

This document describes the RESTful API endpoints available in MiniClaw.

## Base URL

All endpoints are relative to the server base URL, typically `http://127.0.0.1:8787`.

## Authentication

Most endpoints do not require authentication as MiniClaw is designed to run locally. However, Telegram integration requires proper pairing for security.

## Core Endpoints

### Health Check

#### `GET /api/health`

Check if the server is running.

**Response:**
```json
{
  "ok": true,
  "timestamp": "2023-01-01T00:00:00Z"
}
```

### Configuration

#### `GET /api/config`

Get the current configuration.

**Response:**
```json
{
  "ok": true,
  "config": {
    // Full configuration object
  }
}
```

#### `PUT /api/config`

Update the configuration.

**Request Body:**
```json
{
  // Full configuration object
}
```

**Response:**
```json
{
  "ok": true,
  "config": {
    // Updated configuration object
  }
}
```

#### `GET /api/config/raw`

Get the raw configuration text.

**Response:**
```json
{
  "ok": true,
  "path": "/path/to/config.json",
  "raw": "{\n  // raw config JSON\n}"
}
```

#### `PUT /api/config/raw`

Update the raw configuration.

**Request Body:**
```json
{
  "raw": "{\n  // raw config JSON\n}"
}
```

**Response:**
```json
{
  "ok": true,
  "config": {
    // Parsed configuration object
  }
}
```

### Chat

#### `POST /api/chat`

Send a message to the agent.

**Request Body:**
```json
{
  "message": "Hello, how are you?",
  "source": "web",  // optional, defaults to "web"
  "provider_id": "ollama_default"  // optional, uses default if not specified
}
```

**Response:**
```json
{
  "ok": true,
  "trace_id": "trace-1234567890",
  "response": "I'm doing well, thank you for asking!",
  "provider": {
    "id": "ollama_default",
    "type": "ollama",
    "model": "qwen3"
  },
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 10,
    "total_tokens": 35
  },
  "model_calls": 1,
  "tool_runs": []
}
```

### Models

#### `GET /api/models`

List available models from configured providers.

**Query Parameters:**
- `provider_id` (optional): Filter by specific provider

**Response:**
```json
{
  "ok": true,
  "models": [
    {
      "name": "qwen3",
      "size": "4.1GB",
      "digest": "sha256:...",
      "modified_at": "2023-01-01T00:00:00Z"
    }
  ],
  "provider": {
    "id": "ollama_default",
    "name": "Ollama Default",
    "type": "ollama"
  }
}
```

### Memory

#### `GET /api/memory`

List all memory files.

**Query Parameters:**
- `name` (optional): Get specific memory file

**Response:**
```json
{
  "ok": true,
  "files": [
    {
      "name": "soul.md",
      "content": "# Soul\n\nCore stance...",
      "chars": 123
    }
  ],
  "config": {
    // memory configuration
  }
}
```

#### `POST /api/memory/save`

Save a memory file.

**Request Body:**
```json
{
  "name": "notes.md",
  "content": "# My Notes\n\nThese are my notes..."
}
```

**Response:**
```json
{
  "ok": true,
  "file": {
    "name": "notes.md",
    "content": "# My Notes\n\nThese are my notes...",
    "chars": 45
  },
  "files": [
    // list of all memory files
  ]
}
```

### Skills

#### `GET /api/skills`

List all skills.

**Response:**
```json
{
  "ok": true,
  "skills": [
    {
      "id": "issue_triage",
      "title": "Issue Triage",
      "path": "/path/to/skills/issue_triage.md",
      "content": "# Issue Triage\n\nkeywords: bug,incident..."
    }
  ]
}
```

#### `POST /api/skills/save`

Save a skill.

**Request Body:**
```json
{
  "id": "my_skill",
  "content": "# My Skill\n\nkeywords: my,skill\n\nThis is my skill..."
}
```

**Response:**
```json
{
  "ok": true,
  "skill": {
    "id": "my_skill",
    "title": "My Skill",
    "path": "/path/to/skills/my_skill.md",
    "content": "# My Skill\n\nkeywords: my,skill\n\nThis is my skill..."
  },
  "skills": [
    // list of all skills
  ]
}
```

#### `POST /api/skills/delete`

Delete a skill.

**Request Body:**
```json
{
  "id": "my_skill"
}
```

**Response:**
```json
{
  "ok": true,
  "deleted": {
    "id": "my_skill"
  },
  "skills": [
    // list of remaining skills
  ]
}
```

### Tools

#### `POST /api/tools/run`

Run a tool directly.

**Request Body:**
```json
{
  "tool": "list_dir",
  "arguments": {
    "path": "."
  }
}
```

**Response:**
```json
{
  "ok": true,
  "result": {
    "ok": true,
    "tool": "list_dir",
    "result": {
      "path": ".",
      "items": [
        {
          "name": "file.txt",
          "path": "./file.txt",
          "is_dir": false,
          "size_bytes": 1234
        }
      ]
    },
    "duration_seconds": 0.012
  }
}
```

### Plugins

#### `GET /api/plugins`

List all plugins.

**Response:**
```json
{
  "ok": true,
  "plugins": [
    {
      "id": "trace_tag",
      "name": "Trace Tag",
      "description": "Adds trace tags to prompts",
      "version": "1.0.0",
      "enabled": true,
      "loaded": true,
      "path": "/path/to/plugins/trace_tag.py"
    }
  ]
}
```

#### `POST /api/plugins/reload`

Reload all plugins.

**Response:**
```json
{
  "ok": true,
  "plugins": [
    // list of reloaded plugins
  ]
}
```

### Scheduler

#### `GET /api/scheduler`

Get scheduler status.

**Response:**
```json
{
  "ok": true,
  "scheduler": {
    "enabled": true,
    "running": true,
    "next_runs": [
      {
        "id": "health_digest",
        "name": "Health Digest",
        "next_run": "2023-01-01T00:30:00Z"
      }
    ]
  }
}
```

#### `POST /api/scheduler/upsert`

Create or update a scheduler job.

**Request Body:**
```json
{
  "id": "daily_report",
  "name": "Daily Report",
  "prompt": "Generate a daily report of system activity",
  "interval_seconds": 86400,
  "enabled": true,
  "send_to_telegram_chat_id": ""
}
```

**Response:**
```json
{
  "ok": true,
  "job": {
    "id": "daily_report",
    "name": "Daily Report",
    "prompt": "Generate a daily report of system activity",
    "interval_seconds": 86400,
    "enabled": true,
    "send_to_telegram_chat_id": ""
  },
  "scheduler": {
    // updated scheduler status
  }
}
```

#### `POST /api/scheduler/delete`

Delete a scheduler job.

**Request Body:**
```json
{
  "id": "daily_report"
}
```

**Response:**
```json
{
  "ok": true,
  "deleted": {
    "id": "daily_report"
  },
  "scheduler": {
    // updated scheduler status
  }
}
```

#### `POST /api/scheduler/run`

Trigger a scheduler job immediately.

**Request Body:**
```json
{
  "id": "daily_report"
}
```

**Response:**
```json
{
  "ok": true,
  "result": {
    // job execution result
  },
  "scheduler": {
    // updated scheduler status
  }
}
```

### Telegram

#### `POST /api/telegram/restart`

Restart the Telegram poller.

**Response:**
```json
{
  "ok": true,
  "restarted": true,
  "telegram": {
    // telegram service status
  }
}
```

#### `POST /api/telegram/test`

Send a test message to a Telegram chat.

**Request Body:**
```json
{
  "chat_id": "123456789",
  "message": "Test message from MiniClaw"
}
```

**Response:**
```json
{
  "ok": true
}
```

#### `POST /api/telegram/unbind`

Unbind the current Telegram chat.

**Request Body:**
```json
{}
```

**Response:**
```json
{
  "ok": true,
  "result": {
    // unbind result
  },
  "telegram": {
    // updated telegram status
  }
}
```

#### `GET /api/telegram/pairings`

Get pairing status and requests.

**Response:**
```json
{
  "ok": true,
  "pairings": {
    "current_binding": {
      "chat_id": "123456789",
      "username": "user123"
    },
    "pending_requests": [
      {
        "request_id": "req-abc123",
        "chat_id": "987654321",
        "username": "user987",
        "created_at": "2023-01-01T00:00:00Z"
      }
    ]
  }
}
```

#### `POST /api/telegram/pairing/start`

Create a new pairing code.

**Request Body:**
```json
{
  "ttl_seconds": 600  // optional
}
```

**Response:**
```json
{
  "ok": true,
  "pairing": {
    "code": "ABCD-EFGH",
    "expires_at": "2023-01-01T00:10:00Z"
  }
}
```

#### `POST /api/telegram/pairing/confirm`

Confirm a pairing request.

**Request Body:**
```json
{
  "request_id": "req-abc123"
}
```

**Response:**
```json
{
  "ok": true,
  "request": {
    "request_id": "req-abc123",
    "status": "confirmed"
  }
}
```

#### `POST /api/telegram/pairing/reject`

Reject a pairing request.

**Request Body:**
```json
{
  "request_id": "req-abc123"
}
```

**Response:**
```json
{
  "ok": true,
  "request": {
    "request_id": "req-abc123",
    "status": "rejected"
  }
}
```

### Monitoring

#### `GET /api/usage`

Get token usage statistics.

**Query Parameters:**
- `limit` (optional): Maximum number of entries to return (default: 250)

**Response:**
```json
{
  "ok": true,
  "usage": [
    {
      "trace_id": "trace-1234567890",
      "source": "web",
      "provider_id": "ollama_default",
      "provider_type": "ollama",
      "model": "qwen3",
      "prompt_tokens": 25,
      "completion_tokens": 10,
      "total_tokens": 35,
      "timestamp": "2023-01-01T00:00:00Z"
    }
  ]
}
```

#### `GET /api/events`

Get monitoring events.

**Query Parameters:**
- `since_id` (optional): Only return events with ID greater than this
- `limit` (optional): Maximum number of events to return (default: 200)

**Response:**
```json
{
  "ok": true,
  "events": [
    {
      "id": 123,
      "type": "agent.response",
      "message": "Agent produced response",
      "data": {
        // event-specific data
      },
      "timestamp": "2023-01-01T00:00:00Z"
    }
  ],
  "latest_id": 123
}
```

#### `GET /api/history`

Get chat history.

**Query Parameters:**
- `limit` (optional): Maximum number of messages to return (default: 100)

**Response:**
```json
{
  "ok": true,
  "history": [
    {
      "role": "user",
      "content": "Hello!",
      "source": "web",
      "meta": {
        // message metadata
      },
      "timestamp": "2023-01-01T00:00:00Z"
    },
    {
      "role": "assistant",
      "content": "Hi there!",
      "source": "miniclaw",
      "meta": {
        // message metadata
      },
      "timestamp": "2023-01-01T00:00:01Z"
    }
  ]
}
```

### Runtime

#### `GET /api/runtime`

Get runtime information.

**Response:**
```json
{
  "ok": true,
  "runtime": {
    "config_path": "/path/to/config.json",
    "skills_dir": "/path/to/skills",
    "plugins_dir": "/path/to/plugins",
    "memory_dir": "/path/to/memory",
    "jobs_dir": "/path/to/jobs",
    "network_targets": [
      "http://localhost:11434",
      "https://api.telegram.org"
    ],
    "environment": {
      // relevant environment variables
    },
    "loaded_skills": [
      // loaded skills
    ],
    "loaded_plugins": [
      // loaded plugins
    ],
    "providers": {
      // provider configuration
    },
    "memory": {
      // memory configuration and files
    },
    "channels": {
      // channel configuration
    },
    "telegram": {
      // telegram service status
    },
    "scheduler": {
      // scheduler status
    }
  }
}
```