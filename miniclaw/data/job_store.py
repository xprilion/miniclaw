"""Jobs stored as one JSON file per job under ~/.miniclaw/jobs."""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.events import EventLog


def _safe_job_id(job_id: str) -> str:
    return "".join(ch for ch in str(job_id or "").strip().lower() if ch.isalnum() or ch in {"_", "-"}) or ""


def _normalize_job(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(item, dict):
        return None
    job_id = _safe_job_id(str(item.get("id") or ""))
    prompt = str(item.get("prompt") or "").strip()
    if not job_id or not prompt:
        return None
    return {
        "id": job_id,
        "name": str(item.get("name") or job_id),
        "prompt": prompt,
        "interval_seconds": max(10, int(item.get("interval_seconds") or 300)),
        "enabled": bool(item.get("enabled", True)),
        "send_to_telegram_chat_id": str(item.get("send_to_telegram_chat_id") or "").strip(),
    }


class JobStore:
    def __init__(self, jobs_dir: Path, event_log: EventLog) -> None:
        self._jobs_dir = Path(jobs_dir).resolve()
        self._event_log = event_log
        self._lock = threading.Lock()
        self._jobs_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str) -> Path:
        safe = _safe_job_id(job_id)
        if not safe:
            raise ValueError("job_id is required and must be alphanumeric, _ or -")
        p = (self._jobs_dir / f"{safe}.json").resolve()
        if p.parent != self._jobs_dir:
            raise ValueError("Invalid job id")
        return p

    def list(self) -> List[Dict[str, Any]]:
        """Load all jobs from the jobs directory (one file per job)."""
        with self._lock:
            out: List[Dict[str, Any]] = []
            if not self._jobs_dir.exists():
                return out
            for f in sorted(self._jobs_dir.glob("*.json")):
                try:
                    raw = json.loads(f.read_text(encoding="utf-8"))
                    job = _normalize_job(raw)
                    if job:
                        out.append(job)
                except (json.JSONDecodeError, OSError):
                    continue
            return out

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        p = self._path(job_id)
        if not p.exists():
            return None
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            return _normalize_job(raw)
        except (json.JSONDecodeError, OSError):
            return None

    def save(self, job: Dict[str, Any]) -> Dict[str, Any]:
        normalized = _normalize_job(job)
        if not normalized:
            raise ValueError("Job must have id and prompt")
        path = self._path(normalized["id"])
        with self._lock:
            path.write_text(json.dumps(normalized, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self._event_log.add("job_store.saved", "Saved job", {"job_id": normalized["id"]})
        return normalized

    def delete(self, job_id: str) -> bool:
        path = self._path(job_id)
        with self._lock:
            if path.exists():
                path.unlink()
                self._event_log.add("job_store.deleted", "Deleted job", {"job_id": job_id})
                return True
        return False
