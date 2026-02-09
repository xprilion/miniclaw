"""Long-term memory files (soul, user, project, journal)."""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict, List

from ..core.constants import DEFAULT_MEMORY_FILES
from ..core.config import ConfigStore
from ..core.events import EventLog
from ..core.util import utc_now


class MemoryStore:
    def __init__(self, memory_dir: Path, config_store: ConfigStore, event_log: EventLog) -> None:
        self.memory_dir = memory_dir
        self._config_store = config_store
        self._event_log = event_log
        self._lock = threading.Lock()
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.ensure_defaults()

    def _configured_files(self) -> List[str]:
        config = self._config_store.get()
        memory_cfg = config.get("memory") or {}
        files = memory_cfg.get("files") or list(DEFAULT_MEMORY_FILES.keys())
        if not isinstance(files, list):
            files = [files]
        normalized: List[str] = []
        for item in files:
            name = str(item).strip().lower()
            if not name:
                continue
            safe = "".join(ch for ch in name if ch.isalnum() or ch in {"_", "-", "."})
            if not safe.endswith(".md"):
                safe = f"{safe}.md" if safe else ""
            if not safe:
                continue
            if safe not in normalized:
                normalized.append(safe)
        return normalized or list(DEFAULT_MEMORY_FILES.keys())

    def _max_chars(self) -> int:
        config = self._config_store.get()
        memory_cfg = config.get("memory") or {}
        return max(500, int(memory_cfg.get("max_chars_per_file") or 3000))

    def _enabled(self) -> bool:
        config = self._config_store.get()
        memory_cfg = config.get("memory") or {}
        return bool(memory_cfg.get("enabled", True))

    def _file_path(self, name: str) -> Path:
        safe = "".join(ch for ch in str(name).strip().lower() if ch.isalnum() or ch in {"_", "-", "."})
        if not safe.endswith(".md"):
            safe = f"{safe}.md" if safe else ""
        if not safe:
            raise ValueError("Memory file name is required")
        target = (self.memory_dir / safe).resolve()
        try:
            target.relative_to(self.memory_dir.resolve())
        except ValueError as exc:
            raise ValueError("Invalid memory file path") from exc
        return target

    def ensure_defaults(self) -> List[str]:
        created: List[str] = []
        with self._lock:
            for name in self._configured_files():
                path = self._file_path(name)
                if path.exists():
                    continue
                template = DEFAULT_MEMORY_FILES.get(name, f"# {path.stem.title()}\n\n")
                path.write_text(str(template).rstrip() + "\n", encoding="utf-8")
                created.append(name)
        if created:
            self._event_log.add(
                "memory.seeded",
                "Created default memory files",
                {"files": created},
            )
        return created

    def list_files(self) -> List[Dict[str, Any]]:
        self.ensure_defaults()
        items: List[Dict[str, Any]] = []
        for name in self._configured_files():
            path = self._file_path(name)
            if not path.exists():
                continue
            stat = path.stat()
            items.append(
                {
                    "name": name,
                    "path": str(path),
                    "size_bytes": int(stat.st_size),
                    "updated_at_epoch": float(stat.st_mtime),
                }
            )
        return items

    def read(self, name: str) -> Dict[str, Any]:
        self.ensure_defaults()
        path = self._file_path(name)
        if not path.exists():
            raise ValueError(f"Memory file not found: {name}")
        return {
            "name": path.name,
            "path": str(path),
            "content": path.read_text(encoding="utf-8", errors="replace"),
        }

    def read_all(self) -> List[Dict[str, Any]]:
        self.ensure_defaults()
        items: List[Dict[str, Any]] = []
        for file_meta in self.list_files():
            path = self._file_path(file_meta["name"])
            content = path.read_text(encoding="utf-8", errors="replace")
            items.append(
                {
                    **file_meta,
                    "content": content,
                }
            )
        return items

    def save(self, name: str, content: str) -> Dict[str, Any]:
        path = self._file_path(name)
        normalized = str(content or "").rstrip() + "\n"
        with self._lock:
            path.write_text(normalized, encoding="utf-8")
        self._event_log.add(
            "memory.saved",
            "Saved memory file",
            {"name": path.name, "path": str(path)},
        )
        return {
            "name": path.name,
            "path": str(path),
            "content": normalized,
        }

    def prompt_blocks(self) -> List[Dict[str, str]]:
        if not self._enabled():
            return []
        self.ensure_defaults()
        max_chars = self._max_chars()
        blocks: List[Dict[str, str]] = []
        for name in self._configured_files():
            path = self._file_path(name)
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8", errors="replace").strip()
            if not text:
                continue
            if name == "journal.md" and len(text) > max_chars:
                text = text[-max_chars:]
            else:
                text = text[:max_chars]
            blocks.append(
                {
                    "name": name,
                    "content": text,
                }
            )
        return blocks

    def append_journal(
        self,
        *,
        source: str,
        trace_id: str,
        user_message: str,
        assistant_response: str,
        provider_id: str,
        model: str,
    ) -> None:
        if not self._enabled():
            return
        self.ensure_defaults()
        journal_name = "journal.md"
        if journal_name not in self._configured_files():
            journal_name = self._configured_files()[-1]
        path = self._file_path(journal_name)
        entry = (
            f"\n## {utc_now()} [{source}] ({trace_id})\n"
            f"- provider: {provider_id}\n"
            f"- model: {model}\n"
            f"- user: {str(user_message).strip()[:600]}\n"
            f"- assistant: {str(assistant_response).strip()[:1000]}\n"
        )
        with self._lock:
            existing = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
            path.write_text(existing.rstrip() + entry + "\n", encoding="utf-8")
        self._event_log.add(
            "memory.journal.appended",
            "Appended memory journal entry",
            {"name": path.name, "trace_id": trace_id},
        )
