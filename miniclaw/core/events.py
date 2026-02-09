"""Event log and usage tracking."""
from __future__ import annotations

import copy
import threading
from collections import deque
from typing import Any, Dict, List, Optional

from .util import utc_now


class EventLog:
    def __init__(self, max_events: int = 500) -> None:
        self._lock = threading.Lock()
        self._events: deque = deque(maxlen=max_events)
        self._next_id = 1

    def resize(self, max_events: int) -> None:
        safe_max = max(100, int(max_events))
        with self._lock:
            items = list(self._events)
            self._events = deque(items, maxlen=safe_max)

    def add(self, event_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {
            "id": 0,
            "timestamp": utc_now(),
            "type": event_type,
            "message": message,
            "details": details or {},
        }
        with self._lock:
            payload["id"] = self._next_id
            self._next_id += 1
            self._events.append(payload)
        return payload

    def list_since(self, since_id: int = 0, limit: int = 200) -> List[Dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 1000))
        with self._lock:
            items = [event for event in self._events if event["id"] > since_id]
        return items[:safe_limit]

    def latest_id(self) -> int:
        with self._lock:
            return self._events[-1]["id"] if self._events else 0


class UsageTracker:
    def __init__(self, max_entries: int = 2000) -> None:
        self._lock = threading.Lock()
        self._entries: deque = deque(maxlen=max(100, int(max_entries)))

    def add(self, entry: Dict[str, Any]) -> None:
        payload = copy.deepcopy(entry)
        payload.setdefault("timestamp", utc_now())
        with self._lock:
            self._entries.append(payload)

    def snapshot(self, limit: int = 200) -> Dict[str, Any]:
        safe_limit = max(1, min(int(limit), 2000))
        with self._lock:
            recent = list(self._entries)[-safe_limit:]

        totals: Dict[tuple, Dict[str, Any]] = {}
        for item in recent:
            provider_id = str(item.get("provider_id") or "unknown")
            model = str(item.get("model") or "unknown")
            key = (provider_id, model)
            if key not in totals:
                totals[key] = {
                    "provider_id": provider_id,
                    "provider_type": str(item.get("provider_type") or "unknown"),
                    "model": model,
                    "requests": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                }
            bucket = totals[key]
            bucket["requests"] += 1
            bucket["prompt_tokens"] += int(item.get("prompt_tokens") or 0)
            bucket["completion_tokens"] += int(item.get("completion_tokens") or 0)
            bucket["total_tokens"] += int(item.get("total_tokens") or 0)

        totals_list = sorted(
            totals.values(),
            key=lambda item: (int(item.get("total_tokens") or 0), int(item.get("requests") or 0)),
            reverse=True,
        )
        return {
            "totals": totals_list,
            "recent": recent,
            "count": len(recent),
        }
