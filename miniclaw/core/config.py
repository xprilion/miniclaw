"""Configuration load, normalize, and save."""

from __future__ import annotations

import copy
import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from .constants import BASE_DIR, MEMORY_TEMPLATE_DIR
from .events import EventLog
from .util import LOGGER, deep_merge, env_bool


class ConfigStore:
    def __init__(self, path: Path, event_log: EventLog) -> None:
        self.path = path
        self._event_log = event_log
        self._lock = threading.Lock()
        self._config: Dict[str, Any] = {}
        self._load_or_create()

    def _default(self) -> Dict[str, Any]:
        return {
            "server": {
                "host": "127.0.0.1",
                "port": 8787,
            },
            "ollama": {
                "base_url": os.getenv(
                    "OLLAMA_BASE_URL", "https://asusxl-linux.time-royal.ts.net"
                ),
                "model": os.getenv("OLLAMA_MODEL", "gpt-oss:20b"),
                "temperature": 0.2,
                "timeout_seconds": 300,
                "verify_tls": env_bool("OLLAMA_VERIFY_TLS", True),
            },
            "providers": {
                "default_provider_id": "ollama_default",
                "items": [
                    {
                        "id": "ollama_default",
                        "name": "Ollama Default",
                        "type": "ollama",
                        "enabled": True,
                        "base_url": os.getenv(
                            "OLLAMA_BASE_URL", "https://asusxl-linux.time-royal.ts.net"
                        ),
                        "api_key": "",
                        "model": os.getenv("OLLAMA_MODEL", "gpt-oss:20b"),
                        "temperature": 0.2,
                        "timeout_seconds": 300,
                        "verify_tls": env_bool("OLLAMA_VERIFY_TLS", True),
                        "system_prompt_override": "",
                    },
                    {
                        "id": "litellm_default",
                        "name": "LiteLLM Default",
                        "type": "litellm",
                        "enabled": False,
                        "base_url": os.getenv(
                            "LITELLM_BASE_URL", "http://localhost:4000"
                        ),
                        "api_key": os.getenv("LITELLM_API_KEY", ""),
                        "model": os.getenv("LITELLM_MODEL", "gpt-4o-mini"),
                        "temperature": 0.2,
                        "timeout_seconds": 300,
                        "verify_tls": env_bool("LITELLM_VERIFY_TLS", True),
                        "system_prompt_override": "",
                    },
                    {
                        "id": "openrouter_default",
                        "name": "OpenRouter Default",
                        "type": "openrouter",
                        "enabled": False,
                        "base_url": os.getenv(
                            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
                        ),
                        "api_key": os.getenv("OPENROUTER_API_KEY", ""),
                        "model": os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
                        "temperature": 0.2,
                        "timeout_seconds": 300,
                        "verify_tls": env_bool("OPENROUTER_VERIFY_TLS", True),
                        "system_prompt_override": "",
                    },
                ],
            },
            "telegram": {
                "enabled": False,
                "bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
                "allowed_chat_ids": [],
                "binding_mode": "single",
                "poll_interval_seconds": 2,
                "pairing_required": True,
                "pairing_code_ttl_seconds": 600,
                "progress_update_seconds": 12,
            },
            "channels": {
                "active_channel": "telegram",
                "telegram": {},
                "whatsapp_wacli": {
                    "enabled": False,
                    "wacli_command": "wacli",
                    "session": "",
                    "allowed_contacts": [],
                    "poll_interval_seconds": 15,
                },
                "email": {
                    "enabled": False,
                    "imap_host": "",
                    "smtp_host": "",
                    "username": "",
                    "password": "",
                    "from_address": "",
                    "allowed_senders": [],
                    "poll_interval_seconds": 60,
                },
            },
            "agent": {
                "name": "MiniClaw",
                "system_prompt_default": (
                    "You are MiniClaw, optimized for smaller models. "
                    "Be explicit about what actions you took, what data you used, and why."
                ),
                "max_history_messages": 12,
                "enabled_skills": [],
                "enabled_plugins": ["trace_tag"],
                "skill_match_min_score": 2,
                "seeded_default_skills": False,
            },
            "memory": {
                "enabled": True,
                "files": ["soul.md", "user.md", "project.md", "journal.md"],
                "max_chars_per_file": 3000,
            },
            "tools": {
                "enabled": True,
                "max_steps": 4,
                "allow_shell": True,
                "allow_filesystem": True,
                "allow_network": True,
                "allow_browser": True,
                "allow_mcp": True,
                "command_timeout_seconds": 25,
                "output_char_limit": 12000,
                "working_directory": str(BASE_DIR),
            },
            "mcp": {
                "enabled": True,
                "servers": [],
            },
            "monitoring": {
                "max_events": 700,
            },
            "jobs": {
                "enabled": True,
                "jobs": [],
                "seeded_default_jobs": False,
            },
        }

    def _normalize(self, config: Any) -> Dict[str, Any]:
        source = config if isinstance(config, dict) else {}
        merged = deep_merge(self._default(), source)

        merged["server"]["host"] = str(merged["server"].get("host") or "127.0.0.1")
        merged["server"]["port"] = int(merged["server"].get("port") or 8787)

        def normalize_provider(
            provider: Any, fallback_id: str
        ) -> Optional[Dict[str, Any]]:
            if not isinstance(provider, dict):
                return None
            raw_id = str(provider.get("id") or fallback_id).strip().lower()
            provider_id = "".join(
                ch for ch in raw_id if ch.isalnum() or ch in {"_", "-"}
            )
            if not provider_id:
                return None
            provider_type = str(provider.get("type") or "ollama").strip().lower()
            if provider_type not in {
                "ollama",
                "openai_compatible",
                "litellm",
                "openrouter",
            }:
                provider_type = "ollama"
            if provider_type == "ollama":
                base_default = "https://asusxl-linux.time-royal.ts.net"
                model_default = "gpt-oss:20b"
            elif provider_type == "openai_compatible":
                base_default = "https://api.openai.com/v1"
                model_default = "gpt-4o-mini"
            elif provider_type == "litellm":
                base_default = "http://localhost:4000"
                model_default = "gpt-4o-mini"
            elif provider_type == "openrouter":
                base_default = "https://openrouter.ai/api/v1"
                model_default = "openai/gpt-4o-mini"
            else:
                base_default = "https://asusxl-linux.time-royal.ts.net"
                model_default = "gpt-oss:20b"
            return {
                "id": provider_id,
                "name": str(provider.get("name") or provider_id),
                "type": provider_type,
                "enabled": bool(provider.get("enabled", True)),
                "base_url": str(provider.get("base_url") or base_default).rstrip("/"),
                "api_key": str(provider.get("api_key") or ""),
                "model": str(provider.get("model") or model_default),
                "temperature": float(provider.get("temperature") or 0.2),
                "timeout_seconds": max(5, int(provider.get("timeout_seconds") or 300)),
                "verify_tls": bool(provider.get("verify_tls", True)),
                "system_prompt_override": str(
                    provider.get("system_prompt_override") or ""
                ),
            }

        providers_raw = merged.get("providers")
        if not isinstance(providers_raw, dict):
            providers_raw = {}
        providers_items_raw = providers_raw.get("items")
        if not isinstance(providers_items_raw, list):
            providers_items_raw = []
        providers_items: List[Dict[str, Any]] = []
        seen_provider_ids: set[str] = set()
        for idx, item in enumerate(providers_items_raw):
            normalized_item = normalize_provider(
                item, fallback_id=f"provider_{idx + 1}"
            )
            if normalized_item is None:
                continue
            if normalized_item["id"] in seen_provider_ids:
                continue
            seen_provider_ids.add(normalized_item["id"])
            providers_items.append(normalized_item)

        if not providers_items:
            legacy_ollama = (
                merged.get("ollama") if isinstance(merged.get("ollama"), dict) else {}
            )
            legacy_provider = normalize_provider(
                {
                    "id": "ollama_default",
                    "name": "Ollama Default",
                    "type": "ollama",
                    "enabled": True,
                    "base_url": legacy_ollama.get("base_url"),
                    "api_key": "",
                    "model": legacy_ollama.get("model"),
                    "temperature": legacy_ollama.get("temperature"),
                    "timeout_seconds": legacy_ollama.get("timeout_seconds"),
                    "verify_tls": legacy_ollama.get("verify_tls", True),
                    "system_prompt_override": "",
                },
                fallback_id="ollama_default",
            )
            if legacy_provider is not None:
                providers_items.append(legacy_provider)

        if not providers_items:
            defaults = self._default()["providers"]["items"]
            for idx, item in enumerate(defaults):
                normalized_item = normalize_provider(
                    item, fallback_id=f"provider_{idx + 1}"
                )
                if normalized_item is not None:
                    providers_items.append(normalized_item)

        enabled_items = [item for item in providers_items if item.get("enabled")]
        if not enabled_items and providers_items:
            providers_items[0]["enabled"] = True

        provider_ids = [item["id"] for item in providers_items]
        default_provider_id = (
            str(providers_raw.get("default_provider_id") or "").strip().lower()
        )
        if default_provider_id not in provider_ids:
            enabled_ids = [
                item["id"] for item in providers_items if item.get("enabled")
            ]
            default_provider_id = enabled_ids[0] if enabled_ids else provider_ids[0]

        merged["providers"] = {
            "default_provider_id": default_provider_id,
            "items": providers_items,
        }

        provider_index = {item["id"]: item for item in providers_items}
        selected_provider = (
            provider_index.get(default_provider_id) or providers_items[0]
        )
        # Keep legacy ollama section mirrored for compatibility with existing tooling.
        merged["ollama"] = {
            "base_url": str(
                selected_provider.get("base_url")
                or "https://asusxl-linux.time-royal.ts.net"
            ),
            "model": str(selected_provider.get("model") or "gpt-oss:20b"),
            "temperature": float(selected_provider.get("temperature") or 0.2),
            "timeout_seconds": int(selected_provider.get("timeout_seconds") or 300),
            "verify_tls": bool(selected_provider.get("verify_tls", True)),
        }

        raw_channels = merged.get("channels")
        if not isinstance(raw_channels, dict):
            raw_channels = {}
        merged["channels"] = raw_channels
        raw_channel_telegram = raw_channels.get("telegram")
        if isinstance(raw_channel_telegram, dict):
            source_has_telegram = isinstance(source, dict) and "telegram" in source
            if source_has_telegram:
                merged["telegram"] = deep_merge(
                    raw_channel_telegram, merged["telegram"]
                )
            else:
                merged["telegram"] = deep_merge(
                    merged["telegram"], raw_channel_telegram
                )

        merged["telegram"]["enabled"] = bool(merged["telegram"].get("enabled"))
        merged["telegram"]["bot_token"] = str(merged["telegram"].get("bot_token") or "")
        binding_mode = (
            str(merged["telegram"].get("binding_mode") or "single").strip().lower()
        )
        merged["telegram"]["binding_mode"] = (
            "single" if binding_mode not in {"single"} else binding_mode
        )
        raw_ids = merged["telegram"].get("allowed_chat_ids") or []
        if not isinstance(raw_ids, list):
            raw_ids = [raw_ids]
        normalized_ids = [str(item).strip() for item in raw_ids if str(item).strip()]
        # Telegram is intentionally single-user bound. Keep at most one chat id.
        merged["telegram"]["allowed_chat_ids"] = normalized_ids[:1]
        merged["telegram"]["poll_interval_seconds"] = max(
            1, int(merged["telegram"].get("poll_interval_seconds") or 2)
        )
        merged["telegram"]["pairing_required"] = bool(
            merged["telegram"].get("pairing_required", True)
        )
        merged["telegram"]["pairing_code_ttl_seconds"] = max(
            60, int(merged["telegram"].get("pairing_code_ttl_seconds") or 600)
        )
        merged["telegram"]["progress_update_seconds"] = max(
            5, int(merged["telegram"].get("progress_update_seconds") or 12)
        )

        merged["agent"]["name"] = str(merged["agent"].get("name") or "MiniClaw")
        legacy_prompt = str(merged["agent"].get("system_prompt") or "").strip()
        merged["agent"]["system_prompt_default"] = str(
            merged["agent"].get("system_prompt_default")
            or legacy_prompt
            or "You are MiniClaw."
        )
        merged["agent"]["system_prompt"] = merged["agent"]["system_prompt_default"]
        merged["agent"]["max_history_messages"] = max(
            2, int(merged["agent"].get("max_history_messages") or 12)
        )

        enabled_skills = merged["agent"].get("enabled_skills") or []
        if not isinstance(enabled_skills, list):
            enabled_skills = [enabled_skills]
        normalized_skills: List[str] = []
        for skill in enabled_skills:
            skill_id = str(skill).strip()
            if not skill_id:
                continue
            if skill_id.lower() == "transparency":
                continue
            if skill_id not in normalized_skills:
                normalized_skills.append(skill_id)
        merged["agent"]["enabled_skills"] = normalized_skills

        enabled_plugins = merged["agent"].get("enabled_plugins") or []
        if not isinstance(enabled_plugins, list):
            enabled_plugins = [enabled_plugins]
        merged["agent"]["enabled_plugins"] = [
            str(plugin).strip() for plugin in enabled_plugins if str(plugin).strip()
        ]
        merged["agent"]["skill_match_min_score"] = max(
            1, int(merged["agent"].get("skill_match_min_score") or 2)
        )
        merged["agent"]["seeded_default_skills"] = bool(
            merged["agent"].get("seeded_default_skills", False)
        )

        memory_raw = merged.get("memory")
        if not isinstance(memory_raw, dict):
            memory_raw = {}

        # Get memory files from config or use defaults from templates
        memory_files = memory_raw.get("files") or []
        if not memory_files:
            # If no files specified, use default memory files from templates
            if MEMORY_TEMPLATE_DIR.exists():
                memory_files = [
                    f.name
                    for f in MEMORY_TEMPLATE_DIR.iterdir()
                    if f.is_file() and f.suffix == ".md"
                ]

        if not isinstance(memory_files, list):
            memory_files = [memory_files]
        normalized_memory_files: List[str] = []
        for item in memory_files:
            name = str(item).strip().lower()
            if not name:
                continue
            safe = "".join(ch for ch in name if ch.isalnum() or ch in {"_", "-", "."})
            if not safe.endswith(".md"):
                safe = f"{safe}.md" if safe else ""
            if not safe:
                continue
            if safe not in normalized_memory_files:
                normalized_memory_files.append(safe)

        # If still no files, provide default list
        if not normalized_memory_files:
            normalized_memory_files = ["soul.md", "user.md", "project.md", "journal.md"]

        merged["memory"] = {
            "enabled": bool(memory_raw.get("enabled", True)),
            "files": normalized_memory_files,
            "max_chars_per_file": max(
                500, int(memory_raw.get("max_chars_per_file") or 3000)
            ),
        }

        tools_raw = merged.get("tools")
        if not isinstance(tools_raw, dict):
            tools_raw = {}
        merged["tools"] = {
            "enabled": bool(tools_raw.get("enabled", True)),
            "max_steps": max(0, min(12, int(tools_raw.get("max_steps") or 4))),
            "allow_shell": bool(tools_raw.get("allow_shell", True)),
            "allow_filesystem": bool(tools_raw.get("allow_filesystem", True)),
            "allow_network": bool(tools_raw.get("allow_network", True)),
            "allow_browser": bool(tools_raw.get("allow_browser", True)),
            "allow_mcp": bool(tools_raw.get("allow_mcp", True)),
            "command_timeout_seconds": max(
                3, min(300, int(tools_raw.get("command_timeout_seconds") or 25))
            ),
            "output_char_limit": max(
                2000, min(200000, int(tools_raw.get("output_char_limit") or 12000))
            ),
            "working_directory": str(tools_raw.get("working_directory") or BASE_DIR),
            # Preserve additional tool configurations like permissions
            "permissions": tools_raw.get("permissions", {}),
            "user_permissions": tools_raw.get("user_permissions", {}),
            "group_permissions": tools_raw.get("group_permissions", {}),
        }

        mcp_raw = merged.get("mcp")
        if not isinstance(mcp_raw, dict):
            mcp_raw = {}
        mcp_servers_raw = mcp_raw.get("servers")
        if not isinstance(mcp_servers_raw, list):
            mcp_servers_raw = []
        normalized_mcp_servers: List[Dict[str, Any]] = []
        seen_mcp_ids: set[str] = set()
        for idx, item in enumerate(mcp_servers_raw):
            if not isinstance(item, dict):
                continue
            raw_id = str(item.get("id") or f"mcp_{idx + 1}").strip().lower()
            server_id = "".join(ch for ch in raw_id if ch.isalnum() or ch in {"_", "-"})
            if not server_id or server_id in seen_mcp_ids:
                continue
            seen_mcp_ids.add(server_id)
            transport = str(item.get("transport") or "stdio").strip().lower()
            if transport not in {"stdio"}:
                # Don't silently convert unsupported transports to stdio
                # This will cause the MCP manager to properly raise an error
                pass  # Keep the original transport value
            args_raw = item.get("args") or []
            if not isinstance(args_raw, list):
                args_raw = [args_raw]
            env_raw = item.get("env") or {}
            if not isinstance(env_raw, dict):
                env_raw = {}
            normalized_mcp_servers.append(
                {
                    "id": server_id,
                    "name": str(item.get("name") or server_id),
                    "enabled": bool(item.get("enabled", True)),
                    "transport": transport,
                    "command": str(item.get("command") or "").strip(),
                    "args": [str(arg) for arg in args_raw if str(arg).strip()],
                    "cwd": str(item.get("cwd") or "").strip(),
                    "env": {
                        str(key): str(value)
                        for key, value in env_raw.items()
                        if str(key).strip()
                    },
                    "timeout_seconds": max(
                        5, min(300, int(item.get("timeout_seconds") or 30))
                    ),
                }
            )
        merged["mcp"] = {
            "enabled": bool(mcp_raw.get("enabled", True)),
            "servers": normalized_mcp_servers,
        }

        monitoring_raw = merged.get("monitoring")
        if not isinstance(monitoring_raw, dict):
            monitoring_raw = {}
        transparency_raw = merged.get("transparency")
        if isinstance(transparency_raw, dict) and "max_events" not in monitoring_raw:
            monitoring_raw["max_events"] = transparency_raw.get("max_events")
        merged["monitoring"] = {
            "max_events": max(100, int(monitoring_raw.get("max_events") or 700)),
        }
        merged.pop("transparency", None)

        active_channel = (
            str(merged["channels"].get("active_channel") or "telegram").strip().lower()
        )
        if active_channel not in {"telegram", "whatsapp_wacli", "email"}:
            active_channel = "telegram"

        whatsapp_raw = merged["channels"].get("whatsapp_wacli")
        if not isinstance(whatsapp_raw, dict):
            whatsapp_raw = {}
        whatsapp_allowed = whatsapp_raw.get("allowed_contacts") or []
        if not isinstance(whatsapp_allowed, list):
            whatsapp_allowed = [whatsapp_allowed]

        email_raw = merged["channels"].get("email")
        if not isinstance(email_raw, dict):
            email_raw = {}
        email_allowed = email_raw.get("allowed_senders") or []
        if not isinstance(email_allowed, list):
            email_allowed = [email_allowed]

        merged["channels"] = {
            "active_channel": active_channel,
            "telegram": copy.deepcopy(merged["telegram"]),
            "whatsapp_wacli": {
                "enabled": bool(whatsapp_raw.get("enabled", False)),
                "wacli_command": str(whatsapp_raw.get("wacli_command") or "wacli"),
                "session": str(whatsapp_raw.get("session") or ""),
                "allowed_contacts": [
                    str(item).strip() for item in whatsapp_allowed if str(item).strip()
                ],
                "poll_interval_seconds": max(
                    5, int(whatsapp_raw.get("poll_interval_seconds") or 15)
                ),
            },
            "email": {
                "enabled": bool(email_raw.get("enabled", False)),
                "imap_host": str(email_raw.get("imap_host") or ""),
                "smtp_host": str(email_raw.get("smtp_host") or ""),
                "username": str(email_raw.get("username") or ""),
                "password": str(email_raw.get("password") or ""),
                "from_address": str(email_raw.get("from_address") or ""),
                "allowed_senders": [
                    str(item).strip() for item in email_allowed if str(item).strip()
                ],
                "poll_interval_seconds": max(
                    15, int(email_raw.get("poll_interval_seconds") or 60)
                ),
            },
        }

        merged["jobs"]["enabled"] = bool(merged["jobs"].get("enabled", True))
        merged["jobs"]["seeded_default_jobs"] = bool(
            merged["jobs"].get("seeded_default_jobs", False)
        )
        merged["jobs"]["jobs"] = []
        return merged

    def _load_or_create(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            defaults = self._default()
            self.path.write_text(
                json.dumps(defaults, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            self._config = defaults
            self._event_log.add(
                "config.created",
                "Created default config file",
                {"path": str(self.path)},
            )
            LOGGER.info("Created default config at %s", self.path)
            return

        raw = self.path.read_text(encoding="utf-8")
        loaded = json.loads(raw) if raw.strip() else {}
        self._config = self._normalize(loaded)
        self.path.write_text(
            json.dumps(self._config, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        self._event_log.add(
            "config.loaded", "Loaded config file", {"path": str(self.path)}
        )
        LOGGER.info("Loaded config from %s", self.path)

    def get(self) -> Dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._config)

    def save(self, config: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self._normalize(config)
        text = json.dumps(normalized, indent=2, sort_keys=True) + "\n"
        with self._lock:
            self.path.write_text(text, encoding="utf-8")
            self._config = normalized
        self._event_log.add("config.saved", "Config updated", {"path": str(self.path)})
        LOGGER.info("Saved config to %s", self.path)
        return self.get()

    def save_raw(self, raw_text: str) -> Dict[str, Any]:
        loaded = json.loads(raw_text)
        if not isinstance(loaded, dict):
            raise ValueError("Raw config must decode to a JSON object")
        return self.save(loaded)

    def raw_text(self) -> str:
        with self._lock:
            if not self.path.exists():
                return "{}\n"
            return self.path.read_text(encoding="utf-8")
