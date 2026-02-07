"""Shared utilities: logging, time, merge, text, JSON extraction."""
from __future__ import annotations

import copy
import json
import logging
import os
import re
from typing import Any, Dict, Optional

LOGGER = logging.getLogger("miniclaw")


def setup_logging() -> None:
    level_name = str(os.getenv("MINICLAW_LOG_LEVEL", "INFO")).upper().strip()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    LOGGER.info("Logging initialized at level %s", logging.getLevelName(level))


def utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def deep_merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            merged[key] = deep_merge(base.get(key), value)
        return merged
    return copy.deepcopy(override)


def truncate_text(value: str, max_chars: int) -> str:
    text = str(value or "")
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 64] + f"\n...[truncated {len(text) - (max_chars - 64)} chars]"


def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    raw = str(text or "").strip()
    if not raw:
        return None

    candidates = [raw]
    fenced = re.findall(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", raw, flags=re.IGNORECASE)
    candidates.extend(fenced)

    for candidate in candidates:
        stripped = candidate.strip()
        if stripped.startswith("TOOL_CALL:"):
            stripped = stripped[len("TOOL_CALL:") :].strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

    brace_start = raw.find("{")
    brace_end = raw.rfind("}")
    if brace_start >= 0 and brace_end > brace_start:
        fragment = raw[brace_start : brace_end + 1]
        try:
            parsed = json.loads(fragment)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return None
    return None
