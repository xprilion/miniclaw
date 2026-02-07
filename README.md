# MiniClaw

MiniClaw is a minimal OpenClaw-inspired local agent optimized for smaller models. Config and data live in **`~/.miniclaw`**; this repo contains only code.

## Install

**From source (recommended)**

```bash
git clone <repo>
cd miniclaw
uv pip install -e .   # or: pip install -e .
miniclaw install      # or: miniclaw onboard
```

**With uv (if published)**

```bash
uv tool install miniclaw
miniclaw install
```

## Quick Start

1. **Initialize** (creates `~/.miniclaw` with config, memory, skills, plugins)

   ```bash
   miniclaw onboard
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

## Routes

- Landing: `/`
- Chat: `/chat`
- Setup: `/setup`
- Skills: `/skills`
- Scheduler: `/scheduler`
- Monitoring: `/monitoring`

## Telegram Notes

Pairing flow:
1. Enable Telegram in `/setup` and set bot token.
2. Restart poller.
3. Create pairing code.
4. In Telegram: `/pair <CODE>`.
5. Approve request in UI or CLI.
6. MiniClaw allows only one bound Telegram chat at a time; unbind before switching.

Progress updates:
- Telegram tasks send short periodic `MiniClaw update ...` statuses before final output.
- Telegram typing indicator is sent while waiting for completion/chunk delivery.
- For explicit requests like `count 1 to 5, one message at a time`, MiniClaw uses a built-in multi-message delivery path.

Relevant config keys:
- `telegram.pairing_required`
- `telegram.pairing_code_ttl_seconds`
- `telegram.progress_update_seconds`

## Skills

Skills are markdown files under `~/.miniclaw/skills` (or your workspace).

You can CRUD them in `/skills` or via CLI.

Skill matching uses query relevance plus explicit `$skill_id` mentions.

Relevant config key:
- `agent.skill_match_min_score`

## Built-In Scheduler

Scheduler jobs are stored in config (`scheduler.jobs`) and run on interval.

Each job has:
- `id`
- `name`
- `prompt`
- `interval_seconds`
- `enabled`
- `send_to_telegram_chat_id` (optional)

Manage in `/scheduler` or CLI.

## CLI (detailed)

After `miniclaw install` and `uv pip install -e .` (or `pip install -e .`), use the `miniclaw` command. Examples:

```bash
# health / status / models / usage
miniclaw health
miniclaw status
miniclaw models
miniclaw models --provider ollama_default
miniclaw usage --limit 300

# chat
miniclaw agent -m "Hello"
miniclaw chat "Hello" --json --provider ollama_default

# config
miniclaw config get
miniclaw config raw-get
miniclaw config set --file /path/to/config.json

# providers
miniclaw providers list
miniclaw providers save --id local_ollama --name "Local Ollama" --type ollama --base-url http://localhost:11434 --model qwen3
miniclaw providers save --id litellm_proxy --name "LiteLLM Proxy" --type litellm --base-url http://localhost:4000 --model gpt-4o-mini --api-key sk-123456
miniclaw providers save --id openrouter --name "OpenRouter" --type openrouter --base-url https://openrouter.ai/api/v1 --model openai/gpt-4o-mini --api-key sk-or-123456
miniclaw providers default --id local_ollama

# skills / memory / scheduler / telegram
miniclaw skills
miniclaw skill-save --id finance --file /path/to/finance.md
miniclaw memory list
miniclaw memory save --name user.md --stdin
miniclaw scheduler status
miniclaw telegram pair-start --ttl 600
miniclaw telegram pairings
```

## Logging

Moderate logs by default (`INFO`), including startup, poller lifecycle, scheduler, chat requests, and key errors.

Set with:
- `MINICLAW_LOG_LEVEL`

## API Endpoints

- `GET /api/health`
- `GET /api/config`
- `PUT /api/config`
- `GET /api/config/raw`
- `PUT /api/config/raw`
- `GET /api/models` (`provider_id` query param optional)
- `GET /api/usage`
- `GET /api/memory` (`name` query param optional)
- `POST /api/memory/save`
- `GET /api/skills`
- `POST /api/skills/save`
- `POST /api/skills/delete`
- `POST /api/skills/settings`
- `GET /api/plugins`
- `POST /api/plugins/reload`
- `POST /api/chat`
- `GET /api/history`
- `GET /api/events`
- `GET /api/runtime`
- `GET /api/scheduler`
- `POST /api/scheduler/upsert`
- `POST /api/scheduler/delete`
- `POST /api/scheduler/run`
- `POST /api/telegram/restart`
- `POST /api/telegram/test`
- `POST /api/telegram/unbind`
- `GET /api/telegram/pairings`
- `POST /api/telegram/pairing/start`
- `POST /api/telegram/pairing/confirm`
- `POST /api/telegram/pairing/reject`
