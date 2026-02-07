#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def parse_json(text: str) -> Any:
    if not text.strip():
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}


def request_json(
    base_url: str,
    path: str,
    method: str = "GET",
    payload: Optional[Dict[str, Any]] = None,
    raw_body: Optional[str] = None,
    content_type: Optional[str] = None,
) -> Dict[str, Any]:
    url = base_url.rstrip("/") + path
    data = None
    headers = {"Accept": "application/json"}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif raw_body is not None:
        data = raw_body.encode("utf-8")
        headers["Content-Type"] = content_type or "text/plain; charset=utf-8"

    req = urllib.request.Request(url=url, data=data, method=method, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            body = response.read().decode("utf-8", errors="replace")
            parsed = parse_json(body)
            if isinstance(parsed, dict):
                return parsed
            return {"data": parsed}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        parsed = parse_json(body)
        if isinstance(parsed, dict) and parsed.get("error"):
            raise RuntimeError(f"HTTP {exc.code}: {parsed['error']}") from exc
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error: {exc}") from exc


def print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def read_text_file(path: str) -> str:
    file_path = Path(path)
    return file_path.read_text(encoding="utf-8")


def get_workspace_dir() -> Path:
    return Path(os.getenv("MINICLAW_WORKSPACE", "~/.miniclaw")).expanduser().resolve()


def run_install(args: argparse.Namespace) -> int:
    """Create workspace, config, memory, skills, plugins and print setup steps."""
    workspace = Path(getattr(args, "workspace", None) or os.getenv("MINICLAW_WORKSPACE", "~/.miniclaw")).expanduser().resolve()
    print("MiniClaw install")
    print("=" * 50)
    print("\n1. Requirements (run these if not already done):")
    print("   • Python 3.9+")
    print("     Check: python3 --version")
    print("   • uv or pip")
    print("     Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh")
    print("   • Ollama (for local models)")
    print("     Install: https://ollama.com")
    print("     Run: ollama serve  (then e.g. ollama pull qwen3)")
    print("\n2. Creating workspace at:", workspace)
    os.environ["MINICLAW_WORKSPACE"] = str(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "memory").mkdir(exist_ok=True)
    (workspace / "skills").mkdir(exist_ok=True)
    (workspace / "plugins").mkdir(exist_ok=True)
    (workspace / "jobs").mkdir(exist_ok=True)
    print("   Created: memory/, skills/, plugins/, jobs/")
    try:
        from miniclaw.constants import CONFIG_PATH, MEMORY_DIR, PLUGINS_DIR, SKILLS_DIR
        from miniclaw.config import ConfigStore
        from miniclaw.events import EventLog
        from miniclaw.memory_store import MemoryStore
        from miniclaw.skills import SkillRegistry
        from miniclaw.plugins import PluginRegistry

        event_log = EventLog()
        config_store = ConfigStore(CONFIG_PATH, event_log)
        MemoryStore(MEMORY_DIR, config_store, event_log)
        SkillRegistry(SKILLS_DIR, event_log)
        PluginRegistry(PLUGINS_DIR, event_log)
        print("   Config:", CONFIG_PATH)
        print("   Memory files (soul.md, user.md, etc.): created in memory/")
    except Exception as e:
        print("   Warning: could not init config/memory via app modules:", e, file=sys.stderr)
        config_path = workspace / "miniclaw_config.json"
        if not config_path.exists():
            default_config = {
                "server": {"host": "127.0.0.1", "port": 8787},
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "model": "qwen3",
                    "temperature": 0.2,
                    "timeout_seconds": 300,
                    "verify_tls": True,
                },
                "providers": {
                    "default_provider_id": "ollama_default",
                    "items": [
                        {
                            "id": "ollama_default",
                            "name": "Ollama Default",
                            "type": "ollama",
                            "enabled": True,
                            "base_url": "http://localhost:11434",
                            "api_key": "",
                            "model": "qwen3",
                            "temperature": 0.2,
                            "timeout_seconds": 300,
                            "verify_tls": True,
                            "system_prompt_override": "",
                        }
                    ],
                },
                "memory": {"enabled": True, "files": ["soul.md", "user.md", "project.md", "journal.md"], "max_chars_per_file": 3000},
                "tools": {"enabled": True, "max_steps": 4, "working_directory": str(workspace)},
            }
            config_path.write_text(json.dumps(default_config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print("   Wrote minimal config to", config_path)
        for name, content in [
            ("soul.md", "# Soul\n\nCore stance: be clear, concrete, and practical.\n"),
            ("user.md", "# User Profile\n\nPreferred style: direct, low fluff.\n"),
            ("project.md", "# Project Context\n\nArchitecture decisions and constraints.\n"),
            ("journal.md", "# Journal\n\nTimestamped summaries.\n"),
        ]:
            p = workspace / "memory" / name
            if not p.exists():
                p.write_text(content, encoding="utf-8")
                print("   Created memory/", name)
    print("\n3. Make the 'miniclaw' command available (from project root):")
    print("   uv pip install -e .   # or: pip install -e .")
    print("   Then use: miniclaw status  |  miniclaw agent -m \"Hello\"  |  miniclaw gateway")
    print("\n4. Next steps:")
    print("   • Set Ollama URL if not local: edit providers in", workspace / "miniclaw_config.json")
    print("   • Start server: miniclaw gateway   (or: uv run python main.py)")
    print("   • Open: http://127.0.0.1:8787")
    print("   • Chat: miniclaw agent -m \"Your message\"")
    print("\nInstall complete. Run: miniclaw status  to verify.")
    return 0


def run_uninstall(args: argparse.Namespace) -> int:
    """Remove workspace directory (with confirmation)."""
    workspace = Path(getattr(args, "workspace", None) or os.getenv("MINICLAW_WORKSPACE", "~/.miniclaw")).expanduser().resolve()
    if not workspace.exists():
        print("No workspace found at", workspace, "- nothing to uninstall.")
        return 0
    if not getattr(args, "yes", False):
        try:
            reply = input(f"Remove {workspace} and all its contents? [y/N]: ").strip().lower()
        except EOFError:
            reply = "n"
        if reply != "y" and reply != "yes":
            print("Aborted.")
            return 0
    shutil.rmtree(workspace, ignore_errors=True)
    print("Removed", workspace)
    return 0


def run_doctor(args: argparse.Namespace) -> int:
    """Check Python, workspace, config, Ollama, and optional server."""
    workspace = Path(getattr(args, "workspace", None) or os.getenv("MINICLAW_WORKSPACE", "~/.miniclaw")).expanduser().resolve()
    base_url = getattr(args, "base_url", None) or os.getenv("MINICLAW_URL", "http://127.0.0.1:8787")
    checks: List[Tuple[str, bool, str]] = []

    # Python
    ver = sys.version_info
    py_ok = ver >= (3, 9)
    checks.append(("Python 3.9+", py_ok, f"{ver.major}.{ver.minor}.{ver.micro}" if py_ok else "need 3.9+"))

    # Workspace
    ws_ok = workspace.exists()
    checks.append(("Workspace exists", ws_ok, str(workspace)))
    if ws_ok:
        for sub in ("memory", "skills", "plugins", "jobs"):
            d = workspace / sub
            checks.append((f"  {sub}/", d.exists(), str(d)))

    # Config
    config_path = workspace / "miniclaw_config.json"
    config_ok = config_path.exists()
    checks.append(("Config file", config_ok, str(config_path)))
    default_provider: Optional[Dict[str, Any]] = None
    if config_ok:
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            prov = (data.get("providers") or {}).get("items") or []
            default_id = str((data.get("providers") or {}).get("default_provider_id") or "")
            default_provider = next((p for p in prov if isinstance(p, dict) and str(p.get("id") or "") == default_id), prov[0] if prov else None)
            if isinstance(default_provider, dict):
                base = str(default_provider.get("base_url") or "http://localhost:11434")
                checks.append(("  Provider URL", True, base))
        except Exception as e:
            checks.append(("  Config valid", False, str(e)))

    # Ollama / server
    try:
        request_json(base_url, "/api/health")
        checks.append(("Server (MiniClaw)", True, base_url))
    except Exception as e:
        checks.append(("Server (MiniClaw)", False, str(e)))
        ollama_url = "http://localhost:11434"
        if default_provider and isinstance(default_provider, dict):
            ollama_url = str(default_provider.get("base_url") or ollama_url).rstrip("/")
        try:
            req = urllib.request.Request(ollama_url + "/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    checks.append(("Ollama reachable", True, ollama_url))
                else:
                    checks.append(("Ollama reachable", False, f"{ollama_url} returned {resp.status}"))
        except Exception as e2:
            checks.append(("Ollama reachable", False, str(e2)))

    print("MiniClaw doctor")
    print("=" * 50)
    for name, ok, msg in checks:
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {name}: {msg}")
    all_ok = all(c[1] for c in checks)
    print("=" * 50)
    print("All checks passed." if all_ok else "Some checks failed. Run 'install' or fix config.")
    return 0 if all_ok else 1


def run_update(args: argparse.Namespace) -> int:
    """Update dependencies and optionally config defaults."""
    workspace = Path(getattr(args, "workspace", None) or os.getenv("MINICLAW_WORKSPACE", "~/.miniclaw")).expanduser().resolve()
    print("MiniClaw update")
    project_dir = Path(__file__).resolve().parent
    req_file = project_dir / "requirements.txt"
    updated = False
    if req_file.exists():
        uv_cmd = shutil.which("uv")
        if uv_cmd:
            try:
                subprocess.run(
                    [uv_cmd, "pip", "install", "-U", "-r", str(req_file)],
                    cwd=str(project_dir),
                    check=True,
                    capture_output=False,
                )
                print("Dependencies updated (uv pip install -U -r requirements.txt)")
                updated = True
            except subprocess.CalledProcessError as e:
                print("uv pip update failed:", e, file=sys.stderr)
        if not updated:
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-U", "-r", str(req_file)],
                    check=True,
                    capture_output=False,
                )
                print("Dependencies updated from requirements.txt")
                updated = True
            except subprocess.CalledProcessError as e:
                print("pip update failed:", e, file=sys.stderr)
    if not updated:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-U", "miniclaw"], check=True, capture_output=False)
            print("Package miniclaw updated (if installed via pip)")
        except subprocess.CalledProcessError:
            if not updated:
                print("No requirements to update. Use: uv sync  or  pip install -U -r requirements.txt")
    config_path = workspace / "miniclaw_config.json"
    if config_path.exists():
        print("Config at", config_path, "- merge new defaults manually if needed.")
    print("Update complete. Run: miniclaw_cli.py doctor")
    return 0


def run_cli() -> int:
    parser = argparse.ArgumentParser(description="MiniClaw CLI (feature-complete for UI actions)")
    parser.add_argument(
        "--base-url",
        default=os.getenv("MINICLAW_URL", "http://127.0.0.1:8787"),
        help="MiniClaw server base URL (default: http://127.0.0.1:8787)",
    )
    parser.add_argument(
        "--workspace",
        default=os.getenv("MINICLAW_WORKSPACE", "~/.miniclaw"),
        help="Workspace directory (default: ~/.miniclaw)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health", help="Check /api/health")
    install_p = sub.add_parser("install", help="Create workspace and guide through prerequisites")
    install_p.set_defaults(_install_yes=False)
    onboard_p = sub.add_parser("onboard", help="Initialize config & workspace (alias: install)")
    uninstall_p = sub.add_parser("uninstall", help="Remove workspace directory")
    uninstall_p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    doctor_p = sub.add_parser("doctor", help="Check Python, workspace, config, Ollama, server")
    status_p = sub.add_parser("status", help="Show status (alias: doctor)")
    update_p = sub.add_parser("update", help="Update dependencies and existing installation")
    gateway_p = sub.add_parser("gateway", help="Start the server (web + Telegram)")
    gateway_p.add_argument("--host", default=os.getenv("MINICLAW_HOST", "127.0.0.1"), help="Bind host")
    gateway_p.add_argument("--port", type=int, default=int(os.getenv("MINICLAW_PORT", "8787")), help="Bind port")
    models = sub.add_parser("models", help="List provider models")
    models.add_argument("--provider", default="", help="Provider id (default provider if omitted)")
    usage = sub.add_parser("usage", help="Get token usage summary")
    usage.add_argument("--limit", type=int, default=250, help="Max recent usage entries")
    sub.add_parser("runtime", help="Get runtime snapshot")
    sub.add_parser("skills", help="List skills")
    skill_save = sub.add_parser("skill-save", help="Save markdown skill file")
    skill_save.add_argument("--id", required=True, help="Skill id")
    skill_save.add_argument("--file", help="Markdown file path")
    skill_save.add_argument("--stdin", action="store_true", help="Read markdown content from stdin")
    skill_delete = sub.add_parser("skill-delete", help="Delete markdown skill file")
    skill_delete.add_argument("--id", required=True, help="Skill id")

    chat = sub.add_parser("chat", help="Send chat message")
    chat.add_argument("message", nargs="?", help="Message text")
    chat.add_argument("--source", default="cli", help="Message source label")
    chat.add_argument("--provider", default="", help="Provider id override (default provider if omitted)")
    chat.add_argument("--stdin", action="store_true", help="Read message from stdin")
    chat.add_argument("--json", action="store_true", help="Print full JSON response")
    agent_p = sub.add_parser("agent", help="Chat with the agent (alias: chat)")
    agent_p.add_argument("-m", "--message", dest="agent_message", help="Message to send")
    agent_p.add_argument("message_pos", nargs="?", help="Message (alternative to -m)")
    agent_p.add_argument("--provider", default="", help="Provider id override")
    agent_p.add_argument("--json", action="store_true", help="Print full JSON response")
    agent_p.add_argument("--stdin", action="store_true", help="Read message from stdin")

    history = sub.add_parser("history", help="Get chat history")
    history.add_argument("--limit", type=int, default=100)

    events = sub.add_parser("events", help="Get monitoring events")
    events.add_argument("--since-id", type=int, default=0)
    events.add_argument("--limit", type=int, default=120)

    memory = sub.add_parser("memory", help="Memory file operations")
    mem_sub = memory.add_subparsers(dest="memory_command", required=True)
    mem_sub.add_parser("list", help="List memory files and content")
    mem_get = mem_sub.add_parser("get", help="Read one memory file")
    mem_get.add_argument("--name", required=True, help="Memory file name (example: soul.md)")
    mem_save = mem_sub.add_parser("save", help="Save a memory file")
    mem_save.add_argument("--name", required=True, help="Memory file name")
    mem_save.add_argument("--file", help="File to read content from")
    mem_save.add_argument("--stdin", action="store_true", help="Read content from stdin")

    config = sub.add_parser("config", help="Config operations")
    config_sub = config.add_subparsers(dest="config_command", required=True)
    config_sub.add_parser("get", help="Get normalized config JSON")
    config_set = config_sub.add_parser("set", help="PUT config JSON from file")
    config_set.add_argument("--file", required=True, help="Path to config JSON file")
    config_sub.add_parser("raw-get", help="Get raw config text")
    config_raw_set = config_sub.add_parser("raw-set", help="PUT raw config text from file or stdin")
    config_raw_set.add_argument("--file", help="Path to raw JSON file")
    config_raw_set.add_argument("--stdin", action="store_true", help="Read raw JSON from stdin")

    plugins = sub.add_parser("plugins", help="Plugin operations")
    plugins_sub = plugins.add_subparsers(dest="plugins_command", required=True)
    plugins_sub.add_parser("list", help="List plugins")
    plugins_sub.add_parser("reload", help="Reload plugins")

    providers = sub.add_parser("providers", help="Provider operations")
    providers_sub = providers.add_subparsers(dest="providers_command", required=True)
    providers_sub.add_parser("list", help="List configured model providers")
    providers_default = providers_sub.add_parser("default", help="Set default provider")
    providers_default.add_argument("--id", required=True, help="Provider id")
    providers_delete = providers_sub.add_parser("delete", help="Delete provider")
    providers_delete.add_argument("--id", required=True, help="Provider id")
    providers_save = providers_sub.add_parser("save", help="Create or update provider")
    providers_save.add_argument("--id", required=True, help="Provider id")
    providers_save.add_argument("--name", required=True, help="Provider name")
    providers_save.add_argument("--type", choices=["ollama", "openai_compatible"], default="ollama")
    providers_save.add_argument("--base-url", required=True, help="Provider base URL")
    providers_save.add_argument("--model", required=True, help="Model name")
    providers_save.add_argument("--temperature", type=float, default=0.2)
    providers_save.add_argument("--timeout", type=int, default=300, help="Request timeout in seconds (default: 300)")
    providers_save.add_argument("--api-key", default="", help="Optional API key")
    providers_save.add_argument("--prompt-override", default="", help="Optional provider system prompt override")
    providers_save.add_argument("--disable", action="store_true", help="Disable provider")
    providers_save.add_argument("--no-verify-tls", action="store_true", help="Disable TLS verification")

    telegram = sub.add_parser("telegram", help="Telegram operations")
    tg_sub = telegram.add_subparsers(dest="telegram_command", required=True)
    tg_sub.add_parser("restart", help="Restart Telegram poller")

    tg_test = tg_sub.add_parser("test", help="Send Telegram test message")
    tg_test.add_argument("--chat-id", required=True)
    tg_test.add_argument("--message", default="MiniClaw test message")

    tg_sub.add_parser("pairings", help="Get pairing status and requests")

    tg_pair_start = tg_sub.add_parser("pair-start", help="Create Telegram pairing code")
    tg_pair_start.add_argument("--ttl", type=int, default=None, help="Code TTL seconds")

    tg_pair_confirm = tg_sub.add_parser("pair-confirm", help="Confirm pairing request")
    tg_pair_confirm.add_argument("--request-id", required=True)

    tg_pair_reject = tg_sub.add_parser("pair-reject", help="Reject pairing request")
    tg_pair_reject.add_argument("--request-id", required=True)
    tg_sub.add_parser("unbind", help="Remove currently bound Telegram chat")

    scheduler = sub.add_parser("scheduler", help="Scheduler operations")
    sched_sub = scheduler.add_subparsers(dest="scheduler_command", required=True)
    sched_sub.add_parser("status", help="Get scheduler status")
    sched_save = sched_sub.add_parser("save", help="Create or update scheduler job")
    sched_save.add_argument("--id", required=True, help="Job id")
    sched_save.add_argument("--name", required=True, help="Job name")
    sched_save.add_argument("--prompt", required=True, help="Job prompt")
    sched_save.add_argument("--interval", type=int, default=300, help="Interval seconds")
    sched_save.add_argument("--disabled", action="store_true", help="Save as disabled")
    sched_save.add_argument("--telegram-chat-id", default="", help="Optional Telegram chat id for job output")
    sched_delete = sched_sub.add_parser("delete", help="Delete scheduler job")
    sched_delete.add_argument("--id", required=True, help="Job id")
    sched_run = sched_sub.add_parser("run", help="Trigger scheduler job now")
    sched_run.add_argument("--id", required=True, help="Job id")

    args = parser.parse_args()
    base_url = args.base_url
    if args.command == "install":
        return run_install(args)
    if args.command == "onboard":
        return run_install(args)
    if args.command == "uninstall":
        return run_uninstall(args)
    if args.command == "doctor":
        return run_doctor(args)
    if args.command == "status":
        return run_doctor(args)
    if args.command == "update":
        return run_update(args)
    if args.command == "gateway":
        if getattr(args, "host", None):
            os.environ["MINICLAW_HOST"] = str(args.host)
        if getattr(args, "port", None) is not None:
            os.environ["MINICLAW_PORT"] = str(args.port)
        from miniclaw import run
        run()
        return 0
    if args.command == "agent":
        message = (getattr(args, "agent_message", None) or getattr(args, "message_pos", None) or "").strip()
        if getattr(args, "stdin", False):
            message = sys.stdin.read().strip()
        if not message:
            print("Usage: miniclaw agent -m \"Your message\"  or  miniclaw agent \"Your message\"", file=sys.stderr)
            return 1
        result = request_json(
            base_url,
            "/api/chat",
            method="POST",
            payload={
                "message": message,
                "source": "cli",
                "provider_id": getattr(args, "provider", "") or "",
            },
        )
        if getattr(args, "json", False):
            print_json(result)
        else:
            print(result.get("response", ""))
        return 0

    try:
        if args.command == "health":
            print_json(request_json(base_url, "/api/health"))
            return 0

        if args.command == "models":
            provider_q = f"?provider_id={urllib.parse.quote(args.provider)}" if args.provider else ""
            print_json(request_json(base_url, f"/api/models{provider_q}"))
            return 0

        if args.command == "usage":
            print_json(request_json(base_url, f"/api/usage?limit={int(args.limit)}"))
            return 0

        if args.command == "runtime":
            print_json(request_json(base_url, "/api/runtime"))
            return 0

        if args.command == "skills":
            print_json(request_json(base_url, "/api/skills"))
            return 0

        if args.command == "skill-save":
            if bool(args.file) == bool(args.stdin):
                raise RuntimeError("Use exactly one of --file or --stdin for skill-save")
            content = read_text_file(args.file) if args.file else sys.stdin.read()
            if not content.strip():
                raise RuntimeError("Skill content is empty")
            print_json(
                request_json(
                    base_url,
                    "/api/skills/save",
                    method="POST",
                    payload={
                        "id": args.id,
                        "content": content,
                    },
                )
            )
            return 0

        if args.command == "skill-delete":
            print_json(
                request_json(
                    base_url,
                    "/api/skills/delete",
                    method="POST",
                    payload={"id": args.id},
                )
            )
            return 0

        if args.command == "chat":
            if args.stdin:
                message = sys.stdin.read().strip()
            else:
                message = (args.message or "").strip()
            if not message:
                raise RuntimeError("Message is empty. Provide a message or use --stdin.")
            result = request_json(
                base_url,
                "/api/chat",
                method="POST",
                payload={
                    "message": message,
                    "source": args.source,
                    "provider_id": args.provider or "",
                },
            )
            if args.json:
                print_json(result)
            else:
                print(result.get("response", ""))
            return 0

        if args.command == "history":
            print_json(request_json(base_url, f"/api/history?limit={int(args.limit)}"))
            return 0

        if args.command == "events":
            url = f"/api/events?since_id={int(args.since_id)}&limit={int(args.limit)}"
            print_json(request_json(base_url, url))
            return 0

        if args.command == "memory":
            if args.memory_command == "list":
                print_json(request_json(base_url, "/api/memory"))
                return 0

            if args.memory_command == "get":
                path = f"/api/memory?name={urllib.parse.quote(args.name)}"
                print_json(request_json(base_url, path))
                return 0

            if args.memory_command == "save":
                if bool(args.file) == bool(args.stdin):
                    raise RuntimeError("Use exactly one of --file or --stdin for memory save")
                content = read_text_file(args.file) if args.file else sys.stdin.read()
                print_json(
                    request_json(
                        base_url,
                        "/api/memory/save",
                        method="POST",
                        payload={"name": args.name, "content": content},
                    )
                )
                return 0

        if args.command == "config":
            if args.config_command == "get":
                print_json(request_json(base_url, "/api/config"))
                return 0

            if args.config_command == "set":
                payload = json.loads(read_text_file(args.file))
                if not isinstance(payload, dict):
                    raise RuntimeError("Config file must contain a JSON object")
                print_json(request_json(base_url, "/api/config", method="PUT", payload=payload))
                return 0

            if args.config_command == "raw-get":
                data = request_json(base_url, "/api/config/raw")
                print(data.get("raw", ""), end="")
                return 0

            if args.config_command == "raw-set":
                if bool(args.file) == bool(args.stdin):
                    raise RuntimeError("Use exactly one of --file or --stdin for raw-set")
                raw = read_text_file(args.file) if args.file else sys.stdin.read()
                print_json(request_json(base_url, "/api/config/raw", method="PUT", raw_body=raw))
                return 0

        if args.command == "plugins":
            if args.plugins_command == "list":
                print_json(request_json(base_url, "/api/plugins"))
                return 0
            if args.plugins_command == "reload":
                print_json(request_json(base_url, "/api/plugins/reload", method="POST", payload={}))
                return 0

        if args.command == "providers":
            config_payload = request_json(base_url, "/api/config")
            config_obj = config_payload.get("config")
            if not isinstance(config_obj, dict):
                raise RuntimeError("Config payload missing 'config' object")

            providers_obj = config_obj.get("providers")
            if not isinstance(providers_obj, dict):
                providers_obj = {"default_provider_id": "", "items": []}
            items = providers_obj.get("items")
            if not isinstance(items, list):
                items = []

            if args.providers_command == "list":
                print_json({"ok": True, "providers": providers_obj})
                return 0

            if args.providers_command == "default":
                wanted = str(args.id).strip().lower()
                if not wanted:
                    raise RuntimeError("--id is required")
                if not any(str(item.get("id") or "").strip().lower() == wanted for item in items if isinstance(item, dict)):
                    raise RuntimeError(f"Provider not found: {wanted}")
                providers_obj["default_provider_id"] = wanted
                config_obj["providers"] = providers_obj
                updated = request_json(base_url, "/api/config", method="PUT", payload=config_obj)
                print_json({"ok": True, "providers": updated.get("config", {}).get("providers", {})})
                return 0

            if args.providers_command == "delete":
                wanted = str(args.id).strip().lower()
                if not wanted:
                    raise RuntimeError("--id is required")
                kept = [item for item in items if isinstance(item, dict) and str(item.get("id") or "").strip().lower() != wanted]
                if len(kept) == len(items):
                    raise RuntimeError(f"Provider not found: {wanted}")
                if not kept:
                    raise RuntimeError("Cannot delete the last provider")
                if not any(bool(item.get("enabled", True)) for item in kept):
                    kept[0]["enabled"] = True
                default_id = str(providers_obj.get("default_provider_id") or "").strip().lower()
                if default_id == wanted:
                    replacement = next((item for item in kept if bool(item.get("enabled", True))), kept[0])
                    providers_obj["default_provider_id"] = str(replacement.get("id") or "")
                providers_obj["items"] = kept
                config_obj["providers"] = providers_obj
                updated = request_json(base_url, "/api/config", method="PUT", payload=config_obj)
                print_json({"ok": True, "providers": updated.get("config", {}).get("providers", {})})
                return 0

            if args.providers_command == "save":
                provider_id = str(args.id).strip().lower()
                if not provider_id:
                    raise RuntimeError("--id is required")
                provider = {
                    "id": provider_id,
                    "name": str(args.name),
                    "type": str(args.type),
                    "enabled": not bool(args.disable),
                    "base_url": str(args.base_url).strip(),
                    "api_key": str(args.api_key or ""),
                    "model": str(args.model).strip(),
                    "temperature": float(args.temperature),
                    "timeout_seconds": max(5, int(args.timeout)),
                    "verify_tls": not bool(args.no_verify_tls),
                    "system_prompt_override": str(args.prompt_override or ""),
                }
                replaced = False
                new_items = []
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    current_id = str(item.get("id") or "").strip().lower()
                    if current_id == provider_id:
                        new_items.append(provider)
                        replaced = True
                    else:
                        new_items.append(item)
                if not replaced:
                    new_items.append(provider)
                if not any(bool(item.get("enabled", True)) for item in new_items):
                    new_items[0]["enabled"] = True
                default_id = str(providers_obj.get("default_provider_id") or "").strip().lower()
                if not default_id:
                    default_id = provider_id
                if not any(str(item.get("id") or "").strip().lower() == default_id for item in new_items):
                    default_id = provider_id
                providers_obj["items"] = new_items
                providers_obj["default_provider_id"] = default_id
                config_obj["providers"] = providers_obj
                updated = request_json(base_url, "/api/config", method="PUT", payload=config_obj)
                print_json({"ok": True, "providers": updated.get("config", {}).get("providers", {})})
                return 0

        if args.command == "telegram":
            if args.telegram_command == "restart":
                print_json(request_json(base_url, "/api/telegram/restart", method="POST", payload={}))
                return 0

            if args.telegram_command == "test":
                print_json(
                    request_json(
                        base_url,
                        "/api/telegram/test",
                        method="POST",
                        payload={
                            "chat_id": args.chat_id,
                            "message": args.message,
                        },
                    )
                )
                return 0

            if args.telegram_command == "pairings":
                print_json(request_json(base_url, "/api/telegram/pairings"))
                return 0

            if args.telegram_command == "pair-start":
                payload: Dict[str, Any] = {}
                if args.ttl is not None:
                    payload["ttl_seconds"] = int(args.ttl)
                print_json(request_json(base_url, "/api/telegram/pairing/start", method="POST", payload=payload))
                return 0

            if args.telegram_command == "pair-confirm":
                print_json(
                    request_json(
                        base_url,
                        "/api/telegram/pairing/confirm",
                        method="POST",
                        payload={"request_id": args.request_id},
                    )
                )
                return 0

            if args.telegram_command == "pair-reject":
                print_json(
                    request_json(
                        base_url,
                        "/api/telegram/pairing/reject",
                        method="POST",
                        payload={"request_id": args.request_id},
                    )
                )
                return 0

            if args.telegram_command == "unbind":
                print_json(
                    request_json(
                        base_url,
                        "/api/telegram/unbind",
                        method="POST",
                        payload={},
                    )
                )
                return 0

        if args.command == "scheduler":
            if args.scheduler_command == "status":
                print_json(request_json(base_url, "/api/scheduler"))
                return 0

            if args.scheduler_command == "save":
                print_json(
                    request_json(
                        base_url,
                        "/api/scheduler/upsert",
                        method="POST",
                        payload={
                            "id": args.id,
                            "name": args.name,
                            "prompt": args.prompt,
                            "interval_seconds": int(args.interval),
                            "enabled": not bool(args.disabled),
                            "send_to_telegram_chat_id": args.telegram_chat_id,
                        },
                    )
                )
                return 0

            if args.scheduler_command == "delete":
                print_json(
                    request_json(
                        base_url,
                        "/api/scheduler/delete",
                        method="POST",
                        payload={"id": args.id},
                    )
                )
                return 0

            if args.scheduler_command == "run":
                print_json(
                    request_json(
                        base_url,
                        "/api/scheduler/run",
                        method="POST",
                        payload={"id": args.id},
                    )
                )
                return 0

        raise RuntimeError("Unhandled command")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run_cli())
