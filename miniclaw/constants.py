"""Paths, env keys, routes, and default config templates."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

# Package lives in <project_root>/miniclaw/, so project root is parent of this file's parent
_ROOT = Path(__file__).resolve().parent.parent
# Default agent workspace: config, memory, skills, plugins live here
WORKSPACE_DIR = Path(os.getenv("MINICLAW_WORKSPACE", "~/.miniclaw")).expanduser().resolve()
CONFIG_PATH = Path(os.getenv("MINICLAW_CONFIG", str(WORKSPACE_DIR / "miniclaw_config.json"))).expanduser().resolve()
SKILLS_DIR = WORKSPACE_DIR / "skills"
PLUGINS_DIR = WORKSPACE_DIR / "plugins"
MEMORY_DIR = WORKSPACE_DIR / "memory"
JOBS_DIR = WORKSPACE_DIR / "jobs"
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
    "/scheduler": "index.html",
    "/monitoring": "index.html",
    "/transparency": "index.html",
}

PAIRING_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

DEFAULT_SKILL_TEMPLATES: Dict[str, str] = {
    "issue_triage": (
        "# Issue Triage\n\n"
        "keywords: bug,incident,error,regression,fix,root cause\n\n"
        "When queries involve production issues, prioritize:\n"
        "1. observed symptoms,\n"
        "2. likely root causes,\n"
        "3. next diagnostic steps,\n"
        "4. rollback/mitigation options.\n"
    ),
    "research_compare": (
        "# Research Compare\n\n"
        "keywords: compare,comparison,tradeoff,options,evaluate\n\n"
        "For comparison requests, provide concise option tables with clear pros/cons and decision criteria.\n"
    ),
    "ship_plan": (
        "# Ship Plan\n\n"
        "keywords: plan,roadmap,milestone,deliver,ship,launch\n\n"
        "For execution planning, return phased steps with dependencies, risks, and success checks.\n"
    ),
}

DEFAULT_SCHEDULER_JOBS: List[Dict[str, Any]] = [
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

DEFAULT_MEMORY_FILES: Dict[str, str] = {
    "soul.md": (
        "# Soul\n\n"
        "Core stance:\n"
        "- Be clear, concrete, and practical.\n"
        "- Prefer explicit tradeoffs over vague advice.\n"
        "- Keep actions observable.\n"
    ),
    "user.md": (
        "# User Profile\n\n"
        "- Preferred style: direct, low fluff.\n"
        "- Update this file when stable user preferences become clear.\n"
    ),
    "project.md": (
        "# Project Context\n\n"
        "- Record durable architecture decisions, constraints, and known risks.\n"
    ),
    "journal.md": (
        "# Journal\n\n"
        "Append short timestamped summaries of important interactions and outcomes.\n"
    ),
}
