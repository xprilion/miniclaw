"""Application state: config, skills, agent, telegram, scheduler."""
from __future__ import annotations

import copy
import json
import os
from typing import Any, Dict, List

from .constants import (
    CONFIG_PATH,
    DEFAULT_MEMORY_FILES,
    DEFAULT_SCHEDULER_JOBS,
    DEFAULT_SKILL_TEMPLATES,
    ENV_KEYS,
    JOBS_DIR,
    MEMORY_DIR,
    PLUGINS_DIR,
    SKILLS_DIR,
    WEB_DIR,
)
from .config import ConfigStore
from .events import EventLog, UsageTracker
from .job_store import JobStore
from .memory_store import MemoryStore
from .mcp import MCPServerManager
from .plugins import PluginRegistry
from .skills import SkillRegistry
from .telegram import TelegramService
from .scheduler import SchedulerService
from .agent import MiniClawAgent
from .model_client import ModelProviderClient
from .tools import ToolRunner
from .util import LOGGER

class AppState:
    def __init__(self) -> None:
        self.event_log = EventLog(700)
        self.config_store = ConfigStore(CONFIG_PATH, self.event_log)
        loaded = self.config_store.get()
        self.event_log.resize(loaded["monitoring"]["max_events"])

        self.skills = SkillRegistry(SKILLS_DIR, self.event_log)
        self._seed_defaults_once()
        self.plugins = PluginRegistry(PLUGINS_DIR, self.event_log)
        self.plugins.reload()
        loaded = self.config_store.get()
        self.plugins.set_enabled(loaded["agent"].get("enabled_plugins") or [])
        self.usage = UsageTracker()
        self.memory = MemoryStore(MEMORY_DIR, self.config_store, self.event_log)
        self.mcp = MCPServerManager(self.config_store, self.event_log)
        self.tools = ToolRunner(self.config_store, self.event_log, self.mcp)
        self.model_client = ModelProviderClient(self.event_log)
        self.agent = MiniClawAgent(
            config_store=self.config_store,
            event_log=self.event_log,
            skill_registry=self.skills,
            plugin_registry=self.plugins,
            model_client=self.model_client,
            usage_tracker=self.usage,
            memory_store=self.memory,
            tool_runner=self.tools,
        )
        self.telegram = TelegramService(self.config_store, self.event_log, self.agent)
        self.telegram.start_if_enabled()
        self.job_store = JobStore(JOBS_DIR, self.event_log)
        self._migrate_scheduler_jobs_to_store()
        self.scheduler = SchedulerService(
            self.config_store,
            self.job_store,
            self.event_log,
            self.agent,
            self.telegram,
        )
        LOGGER.info(

            "App initialized skills=%d plugins=%d telegram_enabled=%s",
            len(self.skills.list()),
            len(self.plugins.list()),
            bool(loaded["telegram"].get("enabled")),
        )

    def _migrate_scheduler_jobs_to_store(self) -> None:
        """One-time: move jobs from config file into ~/.miniclaw/jobs/ and clear config."""
        existing = self.job_store.list()
        if existing:
            return
        path = self.config_store.path
        if not path.exists():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        in_config = (raw.get("scheduler") or {}).get("jobs") or []
        if not isinstance(in_config, list) or len(in_config) == 0:
            return
        for item in in_config:
            if not isinstance(item, dict):
                continue
            try:
                self.job_store.save(item)
            except (ValueError, OSError):
                continue
        raw["scheduler"] = raw.get("scheduler") or {}
        raw["scheduler"]["jobs"] = []
        path.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.config_store._config = self.config_store._normalize(raw)
        self.event_log.add(
            "scheduler.migrated",
            "Migrated scheduler jobs from config to jobs directory",
            {"count": len(in_config)},
        )
        LOGGER.info("Migrated %d scheduler jobs to %s", len(in_config), JOBS_DIR)

    def _resolve_provider(self, provider_id: str = "") -> Dict[str, Any]:
        config = self.config_store.get()
        providers_cfg = config.get("providers") or {}
        items_raw = providers_cfg.get("items") or []
        items = [item for item in items_raw if isinstance(item, dict)]
        if not items:
            raise ValueError("No model providers configured")

        enabled = [item for item in items if bool(item.get("enabled", True))]
        if not enabled:
            raise ValueError("No enabled model providers configured")

        by_id = {
            str(item.get("id") or "").strip().lower(): item
            for item in items
            if str(item.get("id") or "").strip()
        }
        default_id = str(providers_cfg.get("default_provider_id") or "").strip().lower()
        default_provider = by_id.get(default_id)
        if default_provider is None or not bool(default_provider.get("enabled", True)):
            default_provider = enabled[0]

        requested = str(provider_id or "").strip().lower()
        if requested:
            item = by_id.get(requested)
            if item is None:
                raise ValueError(f"Provider not found: {requested}")
            if not bool(item.get("enabled", True)):
                raise ValueError(f"Provider is disabled: {requested}")
            return copy.deepcopy(item)
        return copy.deepcopy(default_provider)

    def list_models(self, provider_id: str = "") -> Dict[str, Any]:
        provider = self._resolve_provider(provider_id=provider_id)
        models = self.model_client.list_models(provider)
        return {
            "provider": provider,
            "models": models,
        }

    def usage_snapshot(self, limit: int = 250) -> Dict[str, Any]:
        return self.usage.snapshot(limit=limit)

    def _seed_defaults_once(self) -> None:
        config = self.config_store.get()

        seeded_skills = bool(config.get("agent", {}).get("seeded_default_skills", False))
        if not seeded_skills:
            created = self.skills.seed_defaults(DEFAULT_SKILL_TEMPLATES)
            removed_transparency = self.skills.delete_if_exists("transparency")
            enabled_skills = [str(item).strip() for item in config["agent"].get("enabled_skills") or [] if str(item).strip()]
            available_ids = {item["id"] for item in self.skills.list()}
            enabled_present = [item for item in enabled_skills if item in available_ids]
            if not enabled_present:
                enabled_present = [skill_id for skill_id in DEFAULT_SKILL_TEMPLATES.keys() if skill_id in available_ids]
            config["agent"]["enabled_skills"] = enabled_present
            config["agent"]["seeded_default_skills"] = True
            saved = self.config_store.save(config)
            self.event_log.add(
                "seed.skills",
                "Seeded default skills",
                {
                    "created": created,
                    "removed_transparency_skill": removed_transparency,
                    "enabled_skills": saved["agent"].get("enabled_skills") or [],
                },
            )

        config = self.config_store.get()
        seeded_jobs = bool(config.get("scheduler", {}).get("seeded_default_jobs", False))
        if not seeded_jobs:
            existing = self.job_store.list()
            if not existing:
                for item in copy.deepcopy(DEFAULT_SCHEDULER_JOBS):
                    try:
                        self.job_store.save(item)
                    except (ValueError, OSError):
                        pass
            config["scheduler"]["seeded_default_jobs"] = True
            self.config_store.save(config)
            self.event_log.add(
                "seed.scheduler",
                "Seeded default scheduler jobs",
                {"jobs_count": len(self.job_store.list())},
            )

    def apply_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        updated = self.config_store.save(config)
        self.event_log.resize(updated["monitoring"]["max_events"])
        self.memory.ensure_defaults()

        self.plugins.reload()
        self.plugins.set_enabled(updated["agent"].get("enabled_plugins") or [])

        telegram_restarted = self.telegram.restart()

        self.event_log.add(
            "runtime.reloaded",
            "Reloaded runtime after config update",
            {
                "enabled_plugins": updated["agent"].get("enabled_plugins") or [],
                "enabled_skills": updated["agent"].get("enabled_skills") or [],
                "telegram_restarted": telegram_restarted,
            },
        )
        LOGGER.info("Runtime reloaded from config update telegram_restarted=%s", telegram_restarted)
        return updated

    def update_skill_settings(self, enabled_skills: List[str], min_score: int) -> Dict[str, Any]:
        config = self.config_store.get()
        filtered_skills: List[str] = []
        for item in enabled_skills:
            skill_id = str(item).strip()
            if not skill_id:
                continue
            if skill_id.lower() == "transparency":
                continue
            if skill_id not in filtered_skills:
                filtered_skills.append(skill_id)
        config["agent"]["enabled_skills"] = filtered_skills
        config["agent"]["skill_match_min_score"] = max(1, int(min_score))
        updated = self.config_store.save(config)
        self.event_log.add(
            "skill.settings.saved",
            "Updated skill settings",
            {
                "enabled_skills": updated["agent"].get("enabled_skills") or [],
                "skill_match_min_score": updated["agent"].get("skill_match_min_score"),
            },
        )
        return {
            "enabled_skills": updated["agent"].get("enabled_skills") or [],
            "skill_match_min_score": updated["agent"].get("skill_match_min_score"),
        }

    def upsert_scheduler_job(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raw_id = str(payload.get("id") or "").strip().lower()
        job_id = "".join(ch for ch in raw_id if ch.isalnum() or ch in {"_", "-"})
        if not job_id:
            raise ValueError("Scheduler job id is required and must be lowercase letters, numbers, _ or -")
        prompt = str(payload.get("prompt") or "").strip()
        if not prompt:
            raise ValueError("Scheduler job prompt is required")
        name = str(payload.get("name") or job_id)
        interval_seconds = max(10, int(payload.get("interval_seconds") or 300))
        enabled = bool(payload.get("enabled", True))
        send_to_chat_id = str(payload.get("send_to_telegram_chat_id") or "").strip()
        upserted = {
            "id": job_id,
            "name": name,
            "prompt": prompt,
            "interval_seconds": interval_seconds,
            "enabled": enabled,
            "send_to_telegram_chat_id": send_to_chat_id,
        }
        self.job_store.save(upserted)
        self.event_log.add(
            "scheduler.job.saved",
            "Saved scheduler job",
            {"job": upserted},
        )
        return upserted

    def delete_scheduler_job(self, job_id: str) -> Dict[str, Any]:
        wanted = str(job_id or "").strip().lower()
        if not wanted:
            raise ValueError("job_id is required")
        if self.job_store.get(wanted) is None:
            raise ValueError(f"Scheduler job not found: {wanted}")
        self.job_store.delete(wanted)
        self.event_log.add(
            "scheduler.job.deleted",
            "Deleted scheduler job",
            {"job_id": wanted},
        )
        return {"id": wanted}

    def apply_raw_config(self, raw_text: str) -> Dict[str, Any]:
        loaded = json.loads(raw_text)
        if not isinstance(loaded, dict):
            raise ValueError("Raw config must decode to a JSON object")
        return self.apply_config(loaded)

    def runtime_snapshot(self) -> Dict[str, Any]:
        config = self.config_store.get()
        channels = config.get("channels") or {}
        whatsapp = channels.get("whatsapp_wacli") or {}
        email = channels.get("email") or {}
        providers_cfg = config.get("providers") or {}
        providers = [item for item in (providers_cfg.get("items") or []) if isinstance(item, dict)]
        targets = ["https://api.telegram.org"]
        for provider in providers:
            base_url = str(provider.get("base_url") or "").strip()
            if base_url and base_url not in targets:
                targets.append(base_url)
        if str(whatsapp.get("wacli_command") or "").strip():
            targets.append(f"wacli://{whatsapp.get('wacli_command')}")
        if str(email.get("imap_host") or "").strip():
            targets.append(f"imap://{email.get('imap_host')}")
        if str(email.get("smtp_host") or "").strip():
            targets.append(f"smtp://{email.get('smtp_host')}")
        return {
            "config_path": str(self.config_store.path),
            "skills_dir": str(SKILLS_DIR),
            "plugins_dir": str(PLUGINS_DIR),
            "web_dir": str(WEB_DIR),
            "memory_dir": str(MEMORY_DIR),
            "jobs_dir": str(JOBS_DIR),
            "network_targets": targets,
            "environment": {key: os.getenv(key) for key in ENV_KEYS if os.getenv(key) is not None},
            "loaded_skills": [
                {
                    "id": skill["id"],
                    "title": skill["title"],
                    "path": skill["path"],
                }
                for skill in self.skills.list()
            ],
            "loaded_plugins": self.plugins.list(),
            "providers": providers_cfg,
            "memory": {
                "config": config.get("memory") or {},
                "files": self.memory.list_files(),
            },
            "channels": channels,
            "telegram": self.telegram.status(),
            "scheduler": self.scheduler.status(),
        }