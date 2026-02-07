"""Plugin loader and pre_prompt / post_response hooks."""
from __future__ import annotations

import copy
import importlib.util
import threading
import traceback
from pathlib import Path
from typing import Any, Dict, List

from .events import EventLog

class PluginRegistry:
    def __init__(self, plugins_dir: Path, event_log: EventLog) -> None:
        self.plugins_dir = plugins_dir
        self._event_log = event_log
        self._lock = threading.Lock()
        self._plugins: Dict[str, Dict[str, Any]] = {}
        self._enabled: List[str] = []
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

    def reload(self) -> None:
        loaded: Dict[str, Dict[str, Any]] = {}
        for path in sorted(self.plugins_dir.glob("*.py")):
            plugin_id = path.stem
            info: Dict[str, Any] = {
                "id": plugin_id,
                "path": str(path),
                "name": plugin_id,
                "description": "",
                "hooks": {
                    "pre_prompt": False,
                    "post_response": False,
                },
                "error": None,
                "traceback": None,
                "_module": None,
            }
            try:
                spec = importlib.util.spec_from_file_location(f"miniclaw_plugin_{plugin_id}", str(path))
                if spec is None or spec.loader is None:
                    raise RuntimeError("Unable to create plugin import spec")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                metadata = getattr(module, "metadata", {})
                if isinstance(metadata, dict):
                    info["name"] = str(metadata.get("name") or plugin_id)
                    info["description"] = str(metadata.get("description") or "")
                info["hooks"]["pre_prompt"] = callable(getattr(module, "pre_prompt", None))
                info["hooks"]["post_response"] = callable(getattr(module, "post_response", None))
                info["_module"] = module
            except Exception as exc:
                info["error"] = f"{exc.__class__.__name__}: {exc}"
                info["traceback"] = traceback.format_exc(limit=8)
            loaded[plugin_id] = info

        with self._lock:
            self._plugins = loaded
            self._enabled = [plugin_id for plugin_id in self._enabled if plugin_id in self._plugins]

        self._event_log.add(
            "plugins.reloaded",
            "Plugins reloaded",
            {
                "plugins": sorted(loaded.keys()),
            },
        )

    def set_enabled(self, plugin_ids: List[str]) -> None:
        normalized = [str(plugin_id).strip() for plugin_id in plugin_ids if str(plugin_id).strip()]
        with self._lock:
            available = set(self._plugins.keys())
            self._enabled = [plugin_id for plugin_id in normalized if plugin_id in available]
            missing = [plugin_id for plugin_id in normalized if plugin_id not in available]

        if missing:
            self._event_log.add("plugin.missing", "Configured plugin not found", {"plugins": missing})

    def list(self) -> List[Dict[str, Any]]:
        with self._lock:
            enabled = set(self._enabled)
            items: List[Dict[str, Any]] = []
            for plugin_id in sorted(self._plugins.keys()):
                item = self._plugins[plugin_id]
                items.append(
                    {
                        "id": item["id"],
                        "path": item["path"],
                        "name": item["name"],
                        "description": item["description"],
                        "hooks": item["hooks"],
                        "error": item["error"],
                        "traceback": item["traceback"],
                        "enabled": plugin_id in enabled,
                    }
                )
            return items

    def run_pre_prompt(self, context: Dict[str, Any]) -> List[Dict[str, str]]:
        with self._lock:
            plugins = [self._plugins[plugin_id] for plugin_id in self._enabled if plugin_id in self._plugins]

        additions: List[Dict[str, str]] = []
        for plugin in plugins:
            plugin_id = plugin["id"]
            self._event_log.add("plugin.pre_prompt.attempt", "Running pre_prompt hook", {"plugin": plugin_id})

            hook = None
            module = plugin.get("_module")
            if module is not None:
                hook = getattr(module, "pre_prompt", None)
            if not callable(hook):
                self._event_log.add("plugin.pre_prompt.skip", "Plugin has no pre_prompt hook", {"plugin": plugin_id})
                continue

            try:
                result = hook(copy.deepcopy(context))
                self._event_log.add(
                    "plugin.pre_prompt.success",
                    "pre_prompt hook completed",
                    {
                        "plugin": plugin_id,
                        "result": result,
                    },
                )
                if isinstance(result, str) and result.strip():
                    additions.append({"role": "system", "content": result.strip()})
                if isinstance(result, dict):
                    extra_system = result.get("extra_system")
                    if isinstance(extra_system, str) and extra_system.strip():
                        additions.append({"role": "system", "content": extra_system.strip()})
                    messages = result.get("messages")
                    if isinstance(messages, list):
                        for message in messages:
                            if not isinstance(message, dict):
                                continue
                            role = str(message.get("role") or "").strip()
                            content = str(message.get("content") or "").strip()
                            if role and content:
                                additions.append({"role": role, "content": content})
            except Exception as exc:
                self._event_log.add(
                    "plugin.pre_prompt.error",
                    "pre_prompt hook failed",
                    {
                        "plugin": plugin_id,
                        "error": f"{exc.__class__.__name__}: {exc}",
                        "traceback": traceback.format_exc(limit=8),
                    },
                )

        return additions

    def run_post_response(self, context: Dict[str, Any]) -> None:
        with self._lock:
            plugins = [self._plugins[plugin_id] for plugin_id in self._enabled if plugin_id in self._plugins]

        for plugin in plugins:
            plugin_id = plugin["id"]
            self._event_log.add("plugin.post_response.attempt", "Running post_response hook", {"plugin": plugin_id})

            hook = None
            module = plugin.get("_module")
            if module is not None:
                hook = getattr(module, "post_response", None)
            if not callable(hook):
                self._event_log.add("plugin.post_response.skip", "Plugin has no post_response hook", {"plugin": plugin_id})
                continue

            try:
                result = hook(copy.deepcopy(context))
                self._event_log.add(
                    "plugin.post_response.success",
                    "post_response hook completed",
                    {
                        "plugin": plugin_id,
                        "result": result,
                    },
                )
            except Exception as exc:
                self._event_log.add(
                    "plugin.post_response.error",
                    "post_response hook failed",
                    {
                        "plugin": plugin_id,
                        "error": f"{exc.__class__.__name__}: {exc}",
                        "traceback": traceback.format_exc(limit=8),
                    },
                )