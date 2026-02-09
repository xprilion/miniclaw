"""Paths, env keys, routes, and default config templates."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

# Package lives in <project_root>/miniclaw/, so project root is parent of this file's parent
_ROOT = Path(__file__).resolve().parent.parent
# Default agent workspace: config, memory, skills, plugins live here
WORKSPACE_DIR = (
    Path(os.getenv("MINICLAW_WORKSPACE", "~/.miniclaw")).expanduser().resolve()
)
CONFIG_PATH = (
    Path(os.getenv("MINICLAW_CONFIG", str(WORKSPACE_DIR / "miniclaw_config.json")))
    .expanduser()
    .resolve()
)
SKILLS_DIR = WORKSPACE_DIR / "skills"
PLUGINS_DIR = WORKSPACE_DIR / "plugins"
MEMORY_DIR = WORKSPACE_DIR / "memory"
JOBS_DIR = WORKSPACE_DIR / "jobs"
# Template directories for setup
TEMPLATES_DIR = _ROOT / "setup" / "templates"
SKILLS_TEMPLATE_DIR = TEMPLATES_DIR / "skills"
PLUGINS_TEMPLATE_DIR = TEMPLATES_DIR / "plugins"
MEMORY_TEMPLATE_DIR = TEMPLATES_DIR / "memory"
# For static web assets (dev: project root/web; installed: package or project)
WEB_DIR = _ROOT / "web-built"
# Fallback for legacy web assets
LEGACY_WEB_DIR = _ROOT / "web"
# Default cwd for tool runs and config working_directory
BASE_DIR = WORKSPACE_DIR

ENV_KEYS = [
    "MINICLAW_CONFIG",
    "MINICLAW_WORKSPACE",
    "MINICLAW_HOST",
    "MINICLAW_PORT",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "OLLAMA_VERIFY_TLS",
    "LITELLM_BASE_URL",
    "LITELLM_API_KEY",
    "LITELLM_MODEL",
    "LITELLM_VERIFY_TLS",
    "OPENROUTER_BASE_URL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_MODEL",
    "OPENROUTER_VERIFY_TLS",
    "TELEGRAM_BOT_TOKEN",
]

WEB_ROUTES: Dict[str, str] = {
    "/": "index.html",
    "/chat": "index.html",
    "/setup": "index.html",
    "/skills": "index.html",
    "/jobs": "index.html",
    "/monitoring": "index.html",
    "/transparency": "index.html",
}

PAIRING_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

# Default jobs (kept as constants since they're not file-based)
DEFAULT_JOBS: List[Dict[str, Any]] = [
    {
        "id": "health_digest",
        "name": "Health Digest",
        "prompt": "Summarize the latest monitoring events and call out warnings/errors with likely causes.",
        "interval_seconds": 1800,
        "enabled": True,
        "send_to_telegram_chat_id": "",
    },
    {
        "id": "model_readiness",
        "name": "Model Readiness",
        "prompt": "Report current model readiness in 3 bullets: model, connectivity confidence, and any risks.",
        "interval_seconds": 3600,
        "enabled": True,
        "send_to_telegram_chat_id": "",
    },
]
