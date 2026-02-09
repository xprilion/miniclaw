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
import platform

from miniclaw.cli.cli_utils import CLIExperience, CLIStyle

# Global CLI experience instance
cli = CLIExperience("MiniClaw")
style = CLIStyle()


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


def run_gateway_service(args: argparse.Namespace) -> int:
    """Manage the gateway service (start, stop, restart, status)."""
    command = getattr(args, "gateway_command", None)

    if not command:
        return 1

    os_type = platform.system().lower()

    if os_type == "linux":
        return manage_linux_service(command)
    elif os_type == "darwin":  # macOS
        return manage_macos_service(command)
    elif os_type == "windows":
        return manage_windows_service(command)
    else:
        print(style.error(f"Unsupported operating system: {os_type}"))
        return 1


def manage_linux_service(command: str) -> int:
    """Manage systemd service on Linux."""
    service_name = "miniclaw"

    try:
        if command == "start":
            # Check if service exists
            result = subprocess.run(["systemctl", "is-active", service_name],
                                  capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip() == "active":
                print(style.info("Service is already running"))
                return 0

            subprocess.run(["sudo", "systemctl", "start", service_name], check=True)
            print(style.success("Service started successfully"))

        elif command == "stop":
            subprocess.run(["sudo", "systemctl", "stop", service_name], check=True)
            print(style.success("Service stopped successfully"))

        elif command == "restart":
            subprocess.run(["sudo", "systemctl", "restart", service_name], check=True)
            print(style.success("Service restarted successfully"))

        elif command == "status":
            result = subprocess.run(["systemctl", "is-active", service_name],
                                  capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip() == "active":
                print(style.success("Service is running"))
            else:
                print(style.warning("Service is not running"))

        return 0
    except subprocess.CalledProcessError as e:
        print(style.error(f"Failed to {command} service: {e}"))
        return 1
    except Exception as e:
        print(style.error(f"Error managing service: {e}"))
        return 1


def manage_macos_service(command: str) -> int:
    """Manage launchd service on macOS."""
    plist_label = "com.miniclaw.agent"
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{plist_label}.plist"

    try:
        if command == "start":
            if not plist_path.exists():
                print(style.error("Service not installed. Run 'miniclaw service install' first."))
                return 1

            # Check if service is already loaded
            result = subprocess.run(["launchctl", "list", plist_label],
                                  capture_output=True, text=True)
            if result.returncode == 0 and plist_label in result.stdout:
                print(style.info("Service is already loaded"))
                # Check if it's actually running
                return 0

            subprocess.run(["launchctl", "load", str(plist_path)], check=True)
            print(style.success("Service started successfully"))

        elif command == "stop":
            subprocess.run(["launchctl", "unload", str(plist_path)], check=True)
            print(style.success("Service stopped successfully"))

        elif command == "restart":
            subprocess.run(["launchctl", "unload", str(plist_path)],
                          capture_output=True, check=False)
            subprocess.run(["launchctl", "load", str(plist_path)], check=True)
            print(style.success("Service restarted successfully"))

        elif command == "status":
            result = subprocess.run(["launchctl", "list", plist_label],
                                  capture_output=True, text=True)
            if result.returncode == 0 and plist_label in result.stdout:
                print(style.success("Service is loaded"))
            else:
                print(style.warning("Service is not loaded"))

        return 0
    except subprocess.CalledProcessError as e:
        print(style.error(f"Failed to {command} service: {e}"))
        return 1
    except Exception as e:
        print(style.error(f"Error managing service: {e}"))
        return 1


def manage_windows_service(command: str) -> int:
    """Manage Windows service."""
    service_name = "MiniClaw"

    try:
        if command == "start":
            # Check if service exists
            result = subprocess.run(["sc", "query", service_name],
                                  capture_output=True, text=True)
            if "does not exist" in result.stdout:
                print(style.error("Service not installed. Run 'miniclaw service install' first."))
                return 1

            subprocess.run(["sc", "start", service_name], check=True)
            print(style.success("Service started successfully"))

        elif command == "stop":
            subprocess.run(["sc", "stop", service_name], check=True)
            print(style.success("Service stopped successfully"))

        elif command == "restart":
            subprocess.run(["sc", "stop", service_name],
                          capture_output=True, check=False)
            # Wait a bit for service to stop
            import time
            time.sleep(2)
            subprocess.run(["sc", "start", service_name], check=True)
            print(style.success("Service restarted successfully"))

        elif command == "status":
            result = subprocess.run(["sc", "query", service_name],
                                  capture_output=True, text=True)
            if "RUNNING" in result.stdout:
                print(style.success("Service is running"))
            elif "STOPPED" in result.stdout:
                print(style.warning("Service is stopped"))
            else:
                print(style.warning("Service status unknown"))

        return 0
    except subprocess.CalledProcessError as e:
        print(style.error(f"Failed to {command} service: {e}"))
        return 1
    except Exception as e:
        print(style.error(f"Error managing service: {e}"))
        return 1


def run_install_service(args: argparse.Namespace) -> int:
    """Install the service for the current platform."""
    try:
        from miniclaw.setup.init_service import install_service
        success = install_service()
        if success:
            print(style.success("Service installation completed!"))
            print(style.info("Follow the instructions above to complete setup."))
            return 0
        else:
            print(style.error("Service installation failed."))
            return 1
    except ImportError:
        print(style.error("Service installation module not found."))
        return 1
    except Exception as e:
        print(style.error(f"Service installation failed: {e}"))
        return 1


def run_install(args: argparse.Namespace) -> int:
    """Run the enhanced interactive setup wizard."""
    print(style.header("MiniClaw Installation"))
    print(style.info("Starting interactive setup wizard with KeyDB support..."))

    # Show a simple progress indicator
    print(style.info("Launching setup wizard..."))

    from miniclaw.setup.enhanced_setup_wizard import run_enhanced_setup_wizard
    result = run_enhanced_setup_wizard()

    if result == 0:
        print(style.success("Installation completed successfully!"))
        print(style.info("Next steps:"))
        print(f"  {style.list_item('Start the server: ' + style.code('miniclaw gateway'))}")
        print(f"  {style.list_item('Open browser: ' + style.url('http://127.0.0.1:8787'))}")
        chat_example = 'miniclaw agent -m "Hello!"'
        print(f"  {style.list_item('Chat via CLI: ' + style.code(chat_example))}")

        # Offer to set up service
        print(f"\n{style.info('Optional: Set up MiniClaw as a background service')}")
        print(f"  {style.list_item('Run: ' + style.code('miniclaw service install'))}")
        print("  This will set up MiniClaw to run automatically on system startup.")
    else:
        print(style.error("Installation failed. Please check the error messages above."))

    return result


def run_service_command(args: argparse.Namespace) -> int:
    """Handle service management commands."""
    command = getattr(args, "service_command", None)

    if not command:
        return 1

    if command == "install":
        return run_install_service(args)
    elif command == "uninstall":
        return run_uninstall_service(args)
    elif command in ["start", "stop", "restart", "status"]:
        # Create a mock args object with the gateway command
        mock_args = argparse.Namespace()
        mock_args.gateway_command = command
        return run_gateway_service(mock_args)

    return 1


def run_uninstall_service(args: argparse.Namespace) -> int:
    """Uninstall the service for the current platform."""
    os_type = platform.system().lower()

    try:
        if os_type == "linux":
            # Stop and disable service
            subprocess.run(["sudo", "systemctl", "stop", "miniclaw"],
                          capture_output=True, check=False)
            subprocess.run(["sudo", "systemctl", "disable", "miniclaw"],
                          capture_output=True, check=False)
            subprocess.run(["sudo", "rm", "-f", "/etc/systemd/system/miniclaw.service"],
                          check=False)
            subprocess.run(["sudo", "systemctl", "daemon-reload"], check=False)
            print(style.success("Linux service uninstalled"))

        elif os_type == "darwin":  # macOS
            plist_path = Path.home() / "Library" / "LaunchAgents" / "com.miniclaw.agent.plist"
            if plist_path.exists():
                subprocess.run(["launchctl", "unload", str(plist_path)],
                              capture_output=True, check=False)
                plist_path.unlink()
                print(style.success("macOS service uninstalled"))
            else:
                print(style.info("macOS service not found"))

        elif os_type == "windows":
            # Stop and delete service
            subprocess.run(["sc", "stop", "MiniClaw"],
                          capture_output=True, check=False)
            subprocess.run(["sc", "delete", "MiniClaw"],
                          capture_output=True, check=False)
            print(style.success("Windows service uninstalled"))

        else:
            print(style.error(f"Unsupported operating system: {os_type}"))
            return 1

        return 0
    except Exception as e:
        print(style.error(f"Error uninstalling service: {e}"))
        return 1


def run_uninstall(args: argparse.Namespace) -> int:
    """Remove workspace directory (with confirmation) with enhanced styling."""
    workspace = Path(os.getenv("MINICLAW_WORKSPACE", "~/.miniclaw")).expanduser().resolve()

    if not workspace.exists():
        print(style.warning(f"Workspace directory does not exist: {workspace}"))
        return 0

    print(style.header("MiniClaw Uninstall"))
    print(f"Workspace directory: {workspace}")

    # Show what will be removed
    print(style.sub_section("Contents to be removed:"))
    try:
        for item in workspace.iterdir():
            if item.is_dir():
                print(f"  {style.list_item(f'{item.name}/')}")
            else:
                print(f"  {style.list_item(item.name)}")
    except Exception:
        print(style.warning("Could not list directory contents"))

    # Confirm removal
    if not getattr(args, "yes", False):
        print(f"\n{style.warning('This action cannot be undone!')}")
        prompt_text = "Are you sure you want to remove the workspace? (type 'YES' to confirm): "
        confirm = input(f"{style.bold(prompt_text)} ").strip()
        if confirm != "YES":
            print(style.info("Uninstall cancelled."))
            return 0

    # Remove workspace
    try:
        import shutil
        shutil.rmtree(workspace)
        print(style.success(f"Workspace removed successfully: {workspace}"))
        print(style.info("You can reinstall MiniClaw at any time with 'miniclaw install'"))
    except Exception as e:
        print(style.error(f"Failed to remove workspace: {e}"))
        return 1

    return 0


def run_doctor(args: argparse.Namespace) -> int:
    """Check Python, workspace, config, Ollama, and optional server with enhanced styling."""
    workspace_path = getattr(args, "workspace", None) or os.getenv("MINICLAW_WORKSPACE", "~/.miniclaw")
    workspace = Path(workspace_path).expanduser().resolve()
    base_url = getattr(args, "base_url", None) or os.getenv("MINICLAW_URL", "http://127.0.0.1:8787")
    checks: List[Tuple[str, bool, str]] = []

    # Python
    ver = sys.version_info
    py_ok = ver >= (3, 9)
    checks.append(("Python 3.9+", py_ok, f"{ver[0]}.{ver[1]}.{ver[2]}" if py_ok else "need 3.9+"))

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
            providers_data = data.get("providers") or {}
            default_id = str(providers_data.get("default_provider_id") or "")
            default_provider = next(
                (p for p in prov if isinstance(p, dict) and str(p.get("id") or "") == default_id),
                prov[0] if prov else None
            )
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

    print(style.header("MiniClaw System Doctor"))
    print("=" * 50)
    for name, ok, msg in checks:
        status_icon = style.success("OK") if ok else style.error("FAIL")
        print(f"  {status_icon} {name}: {msg}")
    all_ok = all(c[1] for c in checks)
    print("=" * 50)
    if all_ok:
        print(style.success("All checks passed!"))
    else:
        print(style.warning("Some checks failed. Run 'miniclaw install' or fix config."))
    return 0 if all_ok else 1


def run_update(args: argparse.Namespace) -> int:
    """Update dependencies and optionally config defaults with enhanced styling."""
    from miniclaw.cli.cli_utils import CLIProgressBar

    workspace_path = getattr(args, "workspace", None) or os.getenv("MINICLAW_WORKSPACE", "~/.miniclaw")
    workspace = Path(workspace_path).expanduser().resolve()
    print(style.header("MiniClaw Update"))
    project_dir = Path(__file__).resolve().parent
    req_file = project_dir / "requirements.txt"
    updated = False

    if req_file.exists():
        uv_cmd = shutil.which("uv")
        if uv_cmd:
            try:
                print(style.info("Updating dependencies with uv..."))
                # Show progress for dependency update
                progress = CLIProgressBar(100, prefix='Progress:', suffix='Complete', length=30)
                progress.update(20)

                subprocess.run([uv_cmd, "pip", "install", "-r", str(req_file)], check=True)
                progress.update(80)
                updated = True
                progress.finish()
                print(style.success("Dependencies updated successfully"))
            except subprocess.CalledProcessError:
                print(style.error("Failed to update dependencies with uv"))
        else:
            pip_cmd = shutil.which("pip")
            if pip_cmd:
                try:
                    print(style.info("Updating dependencies with pip..."))
                    # Show progress for dependency update
                    progress = CLIProgressBar(100, prefix='Progress:', suffix='Complete', length=30)
                    progress.update(20)

                    subprocess.run([pip_cmd, "install", "-r", str(req_file)], check=True)
                    progress.update(80)
                    updated = True
                    progress.finish()
                    print(style.success("Dependencies updated successfully"))
                except subprocess.CalledProcessError:
                    print(style.error("Failed to update dependencies with pip"))
            else:
                print(style.warning("Neither uv nor pip found. Skipping dependency update."))

    # Update config defaults
    config_path = workspace / "miniclaw_config.json"
    if config_path.exists():
        try:
            from miniclaw.core.config import ConfigStore
            from miniclaw.core.events import EventLog

            print(style.info("Updating config defaults..."))
            event_log = EventLog()
            config_store = ConfigStore(config_path, event_log)
            config_store.save(config_store.get())  # This will apply defaults
            print(style.success("Config defaults updated"))
        except Exception as e:
            print(style.warning(f"Could not update config defaults: {e}"))

    if updated:
        print(style.success("Update completed successfully!"))
    else:
        print(style.info("No updates were performed."))

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
    install_p = sub.add_parser(
        "install",
        help="Create workspace and guide through prerequisites with interactive setup"
    )
    install_p.set_defaults(_install_yes=False)
    sub.add_parser("onboard", help="Initialize config & workspace (alias: install)")

    # Service management commands
    service_p = sub.add_parser("service", help="Manage MiniClaw as a system service")
    service_sub = service_p.add_subparsers(dest="service_command", required=True)
    service_sub.add_parser("install", help="Install MiniClaw as a service")
    service_sub.add_parser("uninstall", help="Uninstall the MiniClaw service")
    service_sub.add_parser("start", help="Start the MiniClaw service")
    service_sub.add_parser("stop", help="Stop the MiniClaw service")
    service_sub.add_parser("restart", help="Restart the MiniClaw service")
    service_sub.add_parser("status", help="Check the status of the MiniClaw service")
    uninstall_p = sub.add_parser("uninstall", help="Remove workspace directory")
    uninstall_p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    sub.add_parser("doctor", help="Check Python, workspace, config, Ollama, server")
    sub.add_parser("status", help="Show status (alias: doctor)")
    sub.add_parser("update", help="Update dependencies and existing installation")
    gateway_p = sub.add_parser(
        "gateway",
        help="Start the server (web + Telegram) or manage as service"
    )
    host_default = os.getenv("MINICLAW_HOST", "127.0.0.1")
    gateway_p.add_argument("--host", default=host_default, help="Bind host")
    port_str = os.getenv("MINICLAW_PORT", "8787")
    gateway_p.add_argument("--port", type=int, default=int(port_str), help="Bind port")
    gateway_sub = gateway_p.add_subparsers(
        dest="gateway_command",
        help="Gateway service management commands",
        required=False
    )
    gateway_sub.add_parser("start", help="Start gateway as a service")
    gateway_sub.add_parser("stop", help="Stop gateway service")
    gateway_sub.add_parser("restart", help="Restart gateway service")
    gateway_sub.add_parser("status", help="Check gateway service status")
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

    jobs = sub.add_parser("jobs", help="Job operations")
    jobs_sub = jobs.add_subparsers(dest="jobs_command", required=True)
    jobs_sub.add_parser("status", help="Get jobs status")
    jobs_save = jobs_sub.add_parser("save", help="Create or update job")
    jobs_save.add_argument("--id", required=True, help="Job id")
    jobs_save.add_argument("--name", required=True, help="Job name")
    jobs_save.add_argument("--prompt", required=True, help="Job prompt")
    jobs_save.add_argument("--interval", type=int, default=300, help="Interval seconds")
    jobs_save.add_argument("--disabled", action="store_true", help="Save as disabled")
    jobs_save.add_argument("--telegram-chat-id", default="", help="Optional Telegram chat id for job output")
    jobs_delete = jobs_sub.add_parser("delete", help="Delete job")
    jobs_delete.add_argument("--id", required=True, help="Job id")
    jobs_run = jobs_sub.add_parser("run", help="Trigger job now")
    jobs_run.add_argument("--id", required=True, help="Job id")

    args = parser.parse_args()
    base_url = args.base_url
    if args.command == "install":
        return run_install(args)
    if args.command == "onboard":
        return run_install(args)
    if args.command == "service":
        return run_service_command(args)
    if args.command == "uninstall":
        return run_uninstall(args)
    if args.command == "doctor" or args.command == "status":
        print(style.header("MiniClaw System Status"))

        # Check Python version
        print(style.sub_section("Python Environment"))
        print(f"  Version: {sys.version.split()[0]}")
        print(f"  Executable: {sys.executable}")

        # Check workspace
        print(style.sub_section("Workspace"))
        workspace = Path(os.getenv("MINICLAW_WORKSPACE", "~/.miniclaw")).expanduser().resolve()
        if workspace.exists():
            print(style.success(f"  Workspace exists: {workspace}"))
        else:
            print(style.warning(f"  Workspace not found: {workspace}"))

        # Check config
        config_path = workspace / "miniclaw_config.json"
        if config_path.exists():
            print(style.success(f"  Config file exists: {config_path}"))
        else:
            print(style.warning(f"  Config file not found: {config_path}"))

        # Check Ollama
        print(style.sub_section("AI Providers"))
        try:
            result = subprocess.run(["ollama", "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(style.success(f"  Ollama: {result.stdout.strip()}"))
            else:
                print(style.warning("  Ollama: Not running or not accessible"))
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print(style.warning("  Ollama: Not installed"))

        # Check server
        print(style.sub_section("Server Status"))
        try:
            health_result = request_json(base_url, "/api/health")
            if health_result.get("ok"):
                print(style.success("  Server: Running"))
            else:
                print(style.warning("  Server: Not responding"))
        except Exception:
            print(style.warning("  Server: Not running"))

        print(f"\n{style.info('Run ' + style.code('miniclaw install') + ' to set up or repair your installation.')}")
        return 0
    if args.command == "status":
        return run_doctor(args)
    if args.command == "update":
        return run_update(args)
    if args.command == "gateway":
        if getattr(args, "gateway_command", None):
            return run_gateway_service(args)
        # Original gateway functionality - start the server directly
        if getattr(args, "host", None):
            os.environ["MINICLAW_HOST"] = str(args.host)
        if getattr(args, "port", None) is not None:
            os.environ["MINICLAW_PORT"] = str(args.port)

        print(style.header("Starting MiniClaw Server"))
        print(style.info("Initializing services..."))

        # Show startup progress
        print(f"{style.list_item('Loading configuration')}")
        print(f"{style.list_item('Initializing services')}")
        print(f"{style.list_item('Starting HTTP server')}")

        from miniclaw import run
        try:
            print(style.success("Server started successfully!"))
            print(style.info("Press Ctrl+C to stop the server"))
            run()
        except KeyboardInterrupt:
            print(f"\n{style.info('Server stopped by user')}")
        except Exception as e:
            print(style.error(f"Server error: {e}"))
            return 1
        return 0
    if args.command == "agent":
        message = (getattr(args, "agent_message", None) or getattr(args, "message_pos", None) or "").strip()
        if getattr(args, "stdin", False):
            message = sys.stdin.read().strip()
        if not message:
            print(style.error("Usage: miniclaw agent -m \"Your message\"  or  miniclaw agent \"Your message\""))
            return 1

        print(style.info("Sending message to MiniClaw..."))
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

        if result.get("ok"):
            if getattr(args, "json", False):
                print_json(result)
            else:
                response = result.get("response", "")
                print(f"\n{style.section('Response:')}")
                print(response)
                duration = result.get("duration_seconds", 0)
                print(f"\n{style.dim(f'Duration: {duration:.2f}s')}")
        else:
            print(style.error(f"Failed to send message: {result.get('error', 'Unknown error')}"))
        return 0

    try:
        if args.command == "health":
            result = request_json(base_url, "/api/health")
            if result.get("ok"):
                print(style.success("Health check passed"))
                print(f"  Timestamp: {result.get('timestamp', 'N/A')}")
            else:
                print(style.error("Health check failed"))
                print(f"  Error: {result.get('error', 'Unknown error')}")
            return 0

        if args.command == "models":
            provider_query = args.provider if args.provider else ""
            provider_q = f"?provider_id={urllib.parse.quote(provider_query)}" if provider_query else ""
            result = request_json(base_url, f"/api/models{provider_q}")
            if result.get("ok"):
                provider_info = result.get("provider", {})
                models = result.get("models", [])

                provider_name = provider_info.get('name', 'Unknown')
                provider_id = provider_info.get('id', 'N/A')
                print(style.section(f"Models ({provider_name} - {provider_id})"))
                print(f"Base URL: {provider_info.get('base_url', 'N/A')}")
                print(f"Model: {provider_info.get('model', 'N/A')}")

                if models:
                    print(f"\n{style.sub_section('Available Models:')}")
                    for model in models:
                        print(f"  {style.list_item(model)}")
                else:
                    print(style.warning("No models available"))
            else:
                print(style.error(f"Failed to fetch models: {result.get('error', 'Unknown error')}"))
            return 0

        if args.command == "usage":
            result = request_json(base_url, f"/api/usage?limit={int(args.limit)}")
            if result.get("ok"):
                usage_data = result.get("usage", {})
                print(style.section("Token Usage Summary"))

                # Show total usage
                total_input = usage_data.get("total_input_tokens", 0)
                total_output = usage_data.get("total_output_tokens", 0)
                total_cost = usage_data.get("estimated_cost_usd", 0)

                print(f"Total Input Tokens:  {style.highlight(str(total_input))}")
                print(f"Total Output Tokens: {style.highlight(str(total_output))}")
                if total_cost > 0:
                    print(f"Estimated Cost:      {style.highlight(f'${total_cost:.4f}')}")

                # Show recent usage
                recent = usage_data.get("recent_usage", [])
                if recent:
                    print(f"\n{style.sub_section('Recent Usage:')}")
                    for item in recent[:10]:  # Show top 10
                        timestamp = item.get("timestamp", "")[:19]  # Truncate to readable format
                        model = item.get("model", "unknown")
                        input_tokens = item.get("input_tokens", 0)
                        output_tokens = item.get("output_tokens", 0)
                        print(f"  {timestamp} | {style.dim(model)} | "
                              f"in: {input_tokens} out: {output_tokens}")
            else:
                print(style.error(f"Failed to fetch usage: {result.get('error', 'Unknown error')}"))
            return 0

        if args.command == "runtime":
            result = request_json(base_url, "/api/runtime")
            if result.get("ok"):
                runtime_data = result.get("runtime", {})
                print(style.section("Runtime Information"))

                # Basic info
                print(f"Config Path:    {runtime_data.get('config_path', 'N/A')}")
                print(f"Workspace:      {runtime_data.get('skills_dir', 'N/A').replace('/skills', '')}")

                # Services status
                telegram_status = runtime_data.get("telegram", {})
                jobs_status = runtime_data.get("jobs", {})

                print(f"\n{style.sub_section('Services Status:')}")
                telegram_enabled = "Enabled" if telegram_status.get("enabled", False) else "Disabled"
                jobs_enabled = "Enabled" if jobs_status.get("enabled", False) else "Disabled"
                print(f"  Telegram: {telegram_enabled}")
                print(f"  Jobs:     {jobs_enabled}")

                # Providers
                providers = runtime_data.get("providers", {}).get("items", [])
                if providers:
                    print(f"\n{style.sub_section('AI Providers:')}")
                    for provider in providers:
                        status = "Enabled" if provider.get("enabled", False) else "Disabled"
                        print(f"  {provider.get('name', 'Unknown')} ({provider.get('type', 'unknown')}): {status}")
                        print(f"    Model: {provider.get('model', 'N/A')}")

                # Loaded components
                skills_count = len(runtime_data.get("loaded_skills", []))
                plugins_count = len(runtime_data.get("loaded_plugins", []))
                print(f"\n{style.sub_section('Loaded Components:')}")
                print(f"  Skills:  {skills_count}")
                print(f"  Plugins: {plugins_count}")

            else:
                print(style.error(f"Failed to fetch runtime info: {result.get('error', 'Unknown error')}"))
            return 0

        if args.command == "skills":
            result = request_json(base_url, "/api/skills")
            if result.get("ok"):
                skills = result.get("skills", [])
                print(style.section(f"Skills ({len(skills)} loaded)"))

                if skills:
                    for skill in skills:
                        status = "Enabled" if skill.get("enabled", True) else "Disabled"
                        status_icon = style.success("") if skill.get("enabled", True) else style.warning("")
                        print(f"\n{style.highlight(skill.get('id', 'unknown'))} {status_icon}")
                        print(f"  Title: {skill.get('title', 'N/A')}")
                        print(f"  Path:  {skill.get('path', 'N/A')}")
                        if skill.get("keywords"):
                            print(f"  Keywords: {', '.join(skill.get('keywords', []))}")
                else:
                    print(style.info("No skills loaded"))
            else:
                print(style.error(f"Failed to fetch skills: {result.get('error', 'Unknown error')}"))
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
                print(style.error("Message is empty. Provide a message or use --stdin."))
                return 1

            print(style.info("Sending message to MiniClaw..."))
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

            if result.get("ok"):
                if args.json:
                    print_json(result)
                else:
                    response = result.get("response", "")
                    print(f"\n{style.section('Response:')}")
                    print(response)
                    duration = result.get("duration_seconds", 0)
                    print(f"\n{style.dim(f'Duration: {duration:.2f}s')}")
            else:
                print(style.error(f"Failed to send message: {result.get('error', 'Unknown error')}"))
            return 0

        if args.command == "history":
            result = request_json(base_url, f"/api/history?limit={int(args.limit)}")
            if result.get("ok"):
                history_items = result.get("history", [])
                print(style.section(f"Chat History ({len(history_items)} items)"))

                for item in history_items:
                    timestamp = item.get("timestamp", "")[:19]  # Truncate to readable format
                    role = item.get("role", "unknown")
                    content = item.get("content", "")[:100] + "..." if len(item.get("content", "")) > 100 else item.get("content", "")

                    role_style = style.success if role == "assistant" else style.info
                    print(f"\n{role_style(role.upper())} [{timestamp}]")
                    print(f"  {content}")
            else:
                print(style.error(f"Failed to fetch history: {result.get('error', 'Unknown error')}"))
            return 0

        if args.command == "events":
            url = f"/api/events?since_id={int(args.since_id)}&limit={int(args.limit)}"
            result = request_json(base_url, url)
            if result.get("ok"):
                events = result.get("events", [])
                print(style.section(f"Events ({len(events)} items)"))
                print(f"Latest ID: {result.get('latest_id', 'N/A')}")

                for event in events:
                    timestamp = event.get("timestamp", "")[:19]  # Truncate to readable format
                    event_type = event.get("type", "unknown")
                    message = event.get("message", "")

                    print(f"\n{style.highlight(event_type)} [{timestamp}]")
                    if message:
                        print(f"  {message}")
                    if event.get("data"):
                        print(f"  Data: {event.get('data')}")
            else:
                print(style.error(f"Failed to fetch events: {result.get('error', 'Unknown error')}"))
            return 0

        if args.command == "memory":
            if args.memory_command == "list":
                result = request_json(base_url, "/api/memory")
                if result.get("ok"):
                    files = result.get("files", [])
                    config = result.get("config", {})
                    print(style.section(f"Memory Files ({len(files)} files)"))
                    print(f"Config: {config}")
                    for file in files:
                        print(f"  {style.list_item(file)}")
                else:
                    print(style.error(f"Failed to list memory files: {result.get('error', 'Unknown error')}"))
                return 0

            if args.memory_command == "get":
                path = f"/api/memory?name={urllib.parse.quote(args.name)}"
                result = request_json(base_url, path)
                if result.get("ok"):
                    file_data = result.get("file", {})
                    files_list = result.get("files", [])
                    print(style.section(f"Memory File: {file_data.get('name', 'unknown')}"))
                    print(f"Path: {file_data.get('path', 'N/A')}")
                    print(f"Size: {file_data.get('size', 0)} bytes")
                    print(f"\n{style.sub_section('Content:')}")
                    print(file_data.get("content", ""))
                else:
                    print(style.error(f"Failed to get memory file: {result.get('error', 'Unknown error')}"))
                return 0

            if args.memory_command == "save":
                if bool(args.file) == bool(args.stdin):
                    print(style.error("Use exactly one of --file or --stdin for memory save"))
                    return 1
                content = read_text_file(args.file) if args.file else sys.stdin.read()
                if not content.strip():
                    print(style.error("Memory content is empty"))
                    return 1
                result = request_json(
                    base_url,
                    "/api/memory/save",
                    method="POST",
                    payload={"name": args.name, "content": content},
                )
                if result.get("ok"):
                    saved_file = result.get("file", {})
                    files_list = result.get("files", [])
                    print(style.success(f"Memory file '{saved_file.get('name', args.name)}' saved successfully"))
                    print(f"Total files: {len(files_list)}")
                else:
                    print(style.error(f"Failed to save memory file: {result.get('error', 'Unknown error')}"))
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
                result = request_json(base_url, "/api/config")
                if result.get("ok"):
                    print(style.section("Current Configuration"))
                    print_json(result.get("config", {}))
                else:
                    print(style.error(f"Failed to get config: {result.get('error', 'Unknown error')}"))
                return 0

            if args.config_command == "set":
                try:
                    payload = json.loads(read_text_file(args.file))
                except json.JSONDecodeError as e:
                    print(style.error(f"Invalid JSON in config file: {e}"))
                    return 1
                if not isinstance(payload, dict):
                    print(style.error("Config file must contain a JSON object"))
                    return 1
                result = request_json(base_url, "/api/config", method="PUT", payload=payload)
                if result.get("ok"):
                    print(style.success("Configuration updated successfully"))
                    print(style.info("Restart the server for changes to take effect"))
                else:
                    print(style.error(f"Failed to update config: {result.get('error', 'Unknown error')}"))
                return 0

            if args.config_command == "raw-get":
                result = request_json(base_url, "/api/config/raw")
                if result.get("ok"):
                    print(result.get("raw", ""), end="")
                else:
                    print(style.error(f"Failed to get raw config: {result.get('error', 'Unknown error')}"))
                return 0

            if args.config_command == "raw-set":
                if bool(args.file) == bool(args.stdin):
                    print(style.error("Use exactly one of --file or --stdin for raw-set"))
                    return 1
                try:
                    raw = read_text_file(args.file) if args.file else sys.stdin.read()
                except Exception as e:
                    print(style.error(f"Failed to read input: {e}"))
                    return 1
                result = request_json(base_url, "/api/config/raw", method="PUT", raw_body=raw)
                if result.get("ok"):
                    print(style.success("Raw configuration updated successfully"))
                else:
                    print(style.error(f"Failed to update raw config: {result.get('error', 'Unknown error')}"))
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

        if args.command == "jobs":
            if args.jobs_command == "status":
                result = request_json(base_url, "/api/jobs")
                if result.get("ok"):
                    jobs_data = result.get("jobs", {})
                    print(style.section("Jobs Status"))

                    status = "Running" if jobs_data.get("running", False) else "Stopped"
                    enabled = "Enabled" if jobs_data.get("enabled", False) else "Disabled"
                    print(f"Service Status: {status}")
                    print(f"Configuration:  {enabled}")

                    jobs_list = jobs_data.get("jobs", [])
                    if jobs_list:
                        print(f"\n{style.sub_section(f'Scheduled Jobs ({len(jobs_list)}):')}")
                        for job in jobs_list:
                            status_icon = style.success("✓") if job.get("enabled", False) else style.warning("⚠")
                            inflight = " (running)" if job.get("inflight", False) else ""
                            print(f"  {status_icon} {style.highlight(job.get('id', 'unknown'))}{inflight}")
                            print(f"    Name: {job.get('name', 'N/A')}")
                            print(f"    Interval: {job.get('interval_seconds', 0)}s")
                            if job.get("next_run_at"):
                                print(f"    Next Run: {job.get('next_run_at', 'N/A')}")
                    else:
                        print(style.info("No jobs configured"))
                else:
                    print(style.error(f"Failed to fetch jobs status: {result.get('error', 'Unknown error')}"))
                return 0

            if args.jobs_command == "save":
                result = request_json(
                    base_url,
                    "/api/jobs/upsert",
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
                if result.get("ok"):
                    print(style.success(f"Job '{args.id}' saved successfully"))
                    job = result.get("job", {})
                    print(f"  Name: {job.get('name', 'N/A')}")
                    print(f"  Interval: {job.get('interval_seconds', 0)}s")
                    status = "Enabled" if job.get("enabled", True) else "Disabled"
                    print(f"  Status: {status}")
                else:
                    print(style.error(f"Failed to save job: {result.get('error', 'Unknown error')}"))
                return 0

            if args.jobs_command == "delete":
                result = request_json(
                    base_url,
                    "/api/jobs/delete",
                    method="POST",
                    payload={"id": args.id},
                )
                if result.get("ok"):
                    print(style.success(f"Job '{args.id}' deleted successfully"))
                else:
                    print(style.error(f"Failed to delete job: {result.get('error', 'Unknown error')}"))
                return 0

            if args.jobs_command == "run":
                result = request_json(
                    base_url,
                    "/api/jobs/run",
                    method="POST",
                    payload={"id": args.id},
                )
                if result.get("ok"):
                    run_result = result.get("result", {})
                    if run_result.get("started", False):
                        print(style.success(f"Job '{args.id}' started successfully"))
                    else:
                        print(style.warning(f"Job '{args.id}' not started: {run_result.get('reason', 'Unknown reason')}"))
                else:
                    print(style.error(f"Failed to run job: {result.get('error', 'Unknown error')}"))
                return 0

        raise RuntimeError("Unhandled command")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run_cli())
