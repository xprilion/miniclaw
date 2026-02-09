"""Agent tools: shell, filesystem, fetch, browser, MCP."""
from __future__ import annotations

import copy
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.config import ConfigStore
from ..core.events import EventLog
from ..services.mcp import MCPServerManager
from ..core.parser import HTMLTextExtractor
from ..security.security import SandboxManager
from ..core.util import extract_json_object, truncate_text


class ToolRunner:
    """Agent tools: shell, filesystem, fetch, browser, MCP."""

    def __init__(self, config_store: ConfigStore, event_log: EventLog, mcp: MCPServerManager,
                 security_managers: Optional[Dict[str, Any]] = None) -> None:
        self._config_store = config_store
        self._event_log = event_log
        self._mcp = mcp
        self._security = security_managers or {}
        self._sandbox = SandboxManager(config_store, event_log)
        self._tool_defs: List[Dict[str, Any]] = [
            {
                "name": "run_command",
                "description": "Run a shell command on the host system.",
                "args_schema": {"command": "string", "cwd": "string(optional)", "timeout_seconds": "int(optional)"},
            },
            {
                "name": "list_dir",
                "description": "List files/directories in a path.",
                "args_schema": {"path": "string(optional)"},
            },
            {
                "name": "read_file",
                "description": "Read a UTF-8 text file.",
                "args_schema": {"path": "string"},
            },
            {
                "name": "write_file",
                "description": "Write UTF-8 text content to a file (overwrites).",
                "args_schema": {"path": "string", "content": "string"},
            },
            {
                "name": "fetch_url",
                "description": "Fetch URL content over HTTP(S).",
                "args_schema": {"url": "string", "timeout_seconds": "int(optional)"},
            },
            {
                "name": "browser_extract",
                "description": "Fetch webpage and extract title, text, and links (headless-lite).",
                "args_schema": {"url": "string", "timeout_seconds": "int(optional)"},
            },
            {
                "name": "mcp_list_servers",
                "description": "List configured MCP servers.",
                "args_schema": {},
            },
            {
                "name": "mcp_list_tools",
                "description": "List tools from a configured MCP server.",
                "args_schema": {"server_id": "string"},
            },
            {
                "name": "mcp_call_tool",
                "description": "Call a tool on a configured MCP server.",
                "args_schema": {"server_id": "string", "tool_name": "string", "arguments": "object(optional)"},
            },
        ]

    def _cfg(self) -> Dict[str, Any]:
        config = self._config_store.get()
        return config.get("tools") or {}

    def _resolve_workdir(self, requested: str = "") -> Path:
        cfg = self._cfg()
        from ..core.constants import BASE_DIR
        configured = str(cfg.get("working_directory") or BASE_DIR).strip() or str(BASE_DIR)
        base = Path(configured).expanduser().resolve()
        request_text = str(requested or "").strip()
        if not request_text:
            return base
        candidate = Path(request_text).expanduser()
        if not candidate.is_absolute():
            candidate = (base / candidate).resolve()
        else:
            candidate = candidate.resolve()
        return candidate

    def _allow(self, feature: str, default: bool = True) -> bool:
        cfg = self._cfg()
        if not bool(cfg.get("enabled", True)):
            return False
        return bool(cfg.get(feature, default))

    def catalog(self, include_mcp_details: bool = False) -> Dict[str, Any]:
        cfg = self._cfg()
        tools: List[Dict[str, Any]] = []
        for item in self._tool_defs:
            name = str(item.get("name") or "")
            if name.startswith("mcp_") and not self._allow("allow_mcp", True):
                continue
            if name in {"run_command"} and not self._allow("allow_shell", True):
                continue
            if name in {"list_dir", "read_file", "write_file"} and not self._allow("allow_filesystem", True):
                continue
            if name in {"fetch_url"} and not self._allow("allow_network", True):
                continue
            if name in {"browser_extract"} and not self._allow("allow_browser", True):
                continue
            tools.append(copy.deepcopy(item))

        payload: Dict[str, Any] = {
            "enabled": bool(cfg.get("enabled", True)),
            "max_steps": max(0, int(cfg.get("max_steps") or 0)),
            "tools": tools,
        }
        if include_mcp_details:
            payload["mcp_servers"] = self._mcp.list_servers()
        return payload

    def _tool_instruction_text(self, tool_defs: List[Dict[str, Any]], max_steps: int) -> str:
        lines = [
            "You can use tools to act on the system before answering. Prefer using them when the user asks to run "
            "something, read/write files, or fetch web content.",
            f"Tool loop budget: {max_steps} calls max for this request.",
            "Use run_command to run shell commands (e.g. list processes, check disk, run scripts). "
            "Use list_dir and read_file for filesystem inspection; use write_file to create or overwrite files. "
            "Use fetch_url or browser_extract to retrieve web pages. Use mcp_* tools when you need a configured "
            "MCP server.",
            "To invoke a tool, respond with exactly one JSON object, no other text:",
            '{"tool":"tool_name","arguments":{"key":"value"}}',
            "When no tool is needed, reply directly to the user.",
            "Available tools:",
        ]
        for item in tool_defs:
            lines.append(f"- {item.get('name')}: {item.get('description')}")
        return "\n".join(lines)

    def agent_prompt_block(self) -> str:
        catalog = self.catalog(include_mcp_details=False)
        tools = catalog.get("tools") or []
        max_steps = int(catalog.get("max_steps") or 0)
        return self._tool_instruction_text(tools, max_steps=max_steps)

    def _args_schema_to_parameters(self, args_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Convert our args_schema (e.g. {'command': 'string', 'cwd': 'string(optional)'}) to Ollama/OpenAI "
        "parameters (JSON Schema)."""
        if not args_schema or not isinstance(args_schema, dict):
            return {"type": "object", "properties": {}, "required": []}
        properties: Dict[str, Dict[str, str]] = {}
        required: List[str] = []
        for key, val in args_schema.items():
            s = str(val or "").strip().lower()
            if "(optional)" in s:
                typ = "string" if "string" in s else "integer" if "int" in s else "object"
                properties[key] = {"type": typ, "description": ""}
            else:
                typ = "string" if "string" in s or not s else "integer" if "int" in s else "object"
                properties[key] = {"type": typ, "description": ""}
                required.append(key)
        return {"type": "object", "properties": properties, "required": required}

    def tool_defs_ollama(self) -> List[Dict[str, Any]]:
        """Return tool definitions in Ollama tool-calling format (tools array for /api/chat)."""
        catalog = self.catalog(include_mcp_details=False)
        tools = catalog.get("tools") or []
        out: List[Dict[str, Any]] = []
        for item in tools:
            name = str(item.get("name") or "")
            if not name:
                continue
            desc = str(item.get("description") or "")
            args_schema = item.get("args_schema")
            params = self._args_schema_to_parameters(args_schema if isinstance(args_schema, dict) else {})
            out.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": desc,
                    "parameters": params,
                },
            })
        return out

    def parse_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        parsed = extract_json_object(text)
        if not isinstance(parsed, dict):
            return None
        tool_name = str(parsed.get("tool") or "").strip()
        if not tool_name:
            return None
        args = parsed.get("arguments")
        if not isinstance(args, dict):
            args = {}
        return {"tool": tool_name, "arguments": args}

    def _run_command(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not self._allow("allow_shell", True):
            raise PermissionError("run_command is disabled in tools config")
        command = str(arguments.get("command") or "").strip()
        if not command:
            raise ValueError("command is required")

        # Sanitize and validate command
        command = self._sandbox.sanitize_input(command, max_length=2000)
        cwd = self._resolve_workdir(str(arguments.get("cwd") or ""))

        # Validate command safety
        if not self._sandbox.validate_command(command, str(cwd)):
            raise PermissionError(f"Command failed security validation: {command}")

        cfg = self._cfg()
        timeout = int(arguments.get("timeout_seconds") or cfg.get("command_timeout_seconds") or 25)
        timeout = max(1, min(timeout, 300))
        started = time.time()
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output_limit = int(cfg.get("output_char_limit") or 12000)
        return {
            "command": command,
            "cwd": str(cwd),
            "exit_code": int(completed.returncode),
            "stdout": truncate_text(completed.stdout or "", output_limit),
            "stderr": truncate_text(completed.stderr or "", output_limit),
            "duration_seconds": round(time.time() - started, 3),
        }

    def _list_dir(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not self._allow("allow_filesystem", True):
            raise PermissionError("list_dir is disabled in tools config")
        path = self._resolve_workdir(str(arguments.get("path") or ""))

        # Validate path safety
        if not self._sandbox.validate_file_path(str(path), "read"):
            raise PermissionError(f"Path access denied: {path}")

        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        if not path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {path}")
        items: List[Dict[str, Any]] = []
        for child in sorted(path.iterdir(), key=lambda item: item.name.lower()):
            try:
                stat = child.stat()
                items.append(
                    {
                        "name": child.name,
                        "path": str(child),
                        "is_dir": child.is_dir(),
                        "size_bytes": int(stat.st_size),
                    }
                )
            except Exception:
                items.append(
                    {
                        "name": child.name,
                        "path": str(child),
                        "is_dir": child.is_dir(),
                        "size_bytes": None,
                    }
                )
        return {"path": str(path), "items": items}

    def _read_file(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not self._allow("allow_filesystem", True):
            raise PermissionError("read_file is disabled in tools config")
        raw_path = str(arguments.get("path") or "").strip()
        if not raw_path:
            raise ValueError("path is required")

        # Sanitize and validate path
        raw_path = self._sandbox.sanitize_input(raw_path, max_length=1000)
        path = self._resolve_workdir(raw_path)

        # Validate path safety
        if not self._sandbox.validate_file_path(str(path), "read"):
            raise PermissionError(f"File access denied: {path}")

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")
        text = path.read_text(encoding="utf-8", errors="replace")
        output_limit = int(self._cfg().get("output_char_limit") or 12000)
        return {"path": str(path), "content": truncate_text(text, output_limit), "chars": len(text)}

    def _write_file(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not self._allow("allow_filesystem", True):
            raise PermissionError("write_file is disabled in tools config")
        raw_path = str(arguments.get("path") or "").strip()
        if not raw_path:
            raise ValueError("path is required")
        content = str(arguments.get("content") or "")

        # Sanitize inputs
        raw_path = self._sandbox.sanitize_input(raw_path, max_length=1000)
        content = self._sandbox.sanitize_input(content, max_length=50000)

        path = self._resolve_workdir(raw_path)

        # Validate path safety for write operations
        if not self._sandbox.validate_file_path(str(path), "write"):
            raise PermissionError(f"File write denied: {path}")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"path": str(path), "chars_written": len(content)}

    def _fetch_url(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not self._allow("allow_network", True):
            raise PermissionError("fetch_url is disabled in tools config")
        url = str(arguments.get("url") or "").strip()
        if not url:
            raise ValueError("url is required")

        # Sanitize URL
        url = self._sandbox.sanitize_input(url, max_length=2000)

        # Basic URL validation
        if not url.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")

        # Check for potentially dangerous URLs
        lower_url = url.lower()
        if any(blocked in lower_url for blocked in ["localhost", "127.0.0.1", "[::1]", "file://"]):
            raise PermissionError("Access to localhost URLs is prohibited")

        # Ensure timeout is an integer
        timeout_float = float(arguments.get("timeout_seconds") or 20)
        timeout = int(max(2, min(timeout_float, 120)))

        # Log the start of the fetch operation
        self._event_log.add(
            "tool.fetch_url.start",
            "Starting URL fetch operation",
            {
                "url": url,
                "timeout": timeout,
            },
        )

        try:
            # Try to use requests library first if available, as it handles SSL better
            try:
                import requests
                self._event_log.add(
                    "tool.fetch_url.requests_used",
                    "Using requests library for URL fetch",
                    {"url": url},
                )

                response = requests.get(
                    url,
                    headers={"User-Agent": "MiniClaw/0.1", "Accept": "*/*"},
                    timeout=timeout,
                    verify=True  # Enable SSL verification
                )

                output_limit = int(self._cfg().get("output_char_limit") or 12000)
                return {
                    "url": url,
                    "status": response.status_code,
                    "content_type": response.headers.get("Content-Type", ""),
                    "body": truncate_text(response.text, output_limit),
                    "bytes": len(response.content),
                }
            except ImportError:
                # Fall back to urllib if requests is not available
                self._event_log.add(
                    "tool.fetch_url.urllib_used",
                    "Using urllib library for URL fetch",
                    {"url": url},
                )

                request = urllib.request.Request(
                    url=url,
                    method="GET",
                    headers={"User-Agent": "MiniClaw/0.1", "Accept": "*/*"},
                )

                # Handle SSL context for HTTPS URLs
                ssl_context = None
                if url.startswith("https://"):
                    try:
                        import ssl
                        ssl_context = ssl.create_default_context()
                    except Exception as ssl_error:
                        self._event_log.add(
                            "tool.fetch_url.ssl_warning",
                            "Failed to create SSL context, proceeding without it",
                            {
                                "url": url,
                                "ssl_error_type": type(ssl_error).__name__,
                                "ssl_error_message": str(ssl_error),
                            },
                        )
                        # Proceed without SSL context if creation fails
                        ssl_context = None

                # Convert timeout to int to avoid float issues
                int_timeout = int(timeout)
                with urllib.request.urlopen(request, timeout=int_timeout, context=ssl_context) as response:
                    raw = response.read()
                    body = raw.decode("utf-8", errors="replace")
                    content_type = response.headers.get("Content-Type", "")
                    output_limit = int(self._cfg().get("output_char_limit") or 12000)
                    return {
                        "url": url,
                        "status": int(response.status),
                        "content_type": content_type,
                        "body": truncate_text(body, output_limit),
                        "bytes": len(raw),
                    }
        except Exception as e:
            # Log the full error for debugging
            self._event_log.add(
                "tool.fetch_url.error",
                "URL fetch failed with detailed error",
                {
                    "url": url,
                    "timeout_used": timeout,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "error_args": getattr(e, 'args', []),
                },
            )
            # Re-raise the exception
            raise

    def _browser_extract(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not self._allow("allow_browser", True):
            raise PermissionError("browser_extract is disabled in tools config")
        fetched = self._fetch_url(arguments)
        body = str(fetched.get("body") or "")
        parser = HTMLTextExtractor()
        parser.feed(body)
        links = parser.links[:120]
        output_limit = int(self._cfg().get("output_char_limit") or 12000)
        return {
            "url": fetched.get("url"),
            "status": fetched.get("status"),
            "title": parser.title,
            "text": truncate_text(parser.text(max_chars=output_limit), output_limit),
            "links": links,
            "link_count": len(links),
        }

    def run(self, tool_name: str, arguments: Optional[Dict[str, Any]],
            trace: Optional[Dict[str, Any]] = None, user_id: str = "default") -> Dict[str, Any]:
        name = str(tool_name or "").strip()
        args = arguments if isinstance(arguments, dict) else {}
        trace_details = trace if isinstance(trace, dict) else {}
        started = time.time()

        # Check permissions before executing
        if hasattr(self, '_security') and self._security.get("permissions"):
            permissions_manager = self._security["permissions"]
            if not permissions_manager.check_tool_permission(name, user_id=user_id, context=args):
                raise PermissionError(f"Permission denied for tool: {name}")

        # Apply rate limiting
        if hasattr(self, '_security') and self._security.get("rate_limiter"):
            rate_limiter = self._security["rate_limiter"]
            # Extract IP from trace if available
            ip_address = trace_details.get("client_ip", "") if trace_details else ""
            if not rate_limiter.check_rate_limit(user_id=user_id, ip_address=ip_address):
                raise PermissionError("Rate limit exceeded")

        self._event_log.add(
            "tool.run.start",
            "Tool execution started",
            {"tool": name, "arguments": args, "trace": trace_details, "user_id": user_id},
        )
        try:
            if name == "run_command":
                result = self._run_command(args)
            elif name == "list_dir":
                result = self._list_dir(args)
            elif name == "read_file":
                result = self._read_file(args)
            elif name == "write_file":
                result = self._write_file(args)
            elif name == "fetch_url":
                result = self._fetch_url(args)
            elif name == "browser_extract":
                result = self._browser_extract(args)
            elif name == "mcp_list_servers":
                if not self._allow("allow_mcp", True):
                    raise PermissionError("MCP tools are disabled in tools config")
                result = {"servers": self._mcp.list_servers()}
            elif name == "mcp_list_tools":
                if not self._allow("allow_mcp", True):
                    raise PermissionError("MCP tools are disabled in tools config")
                result = self._mcp.list_tools(str(args.get("server_id") or ""))
            elif name == "mcp_call_tool":
                if not self._allow("allow_mcp", True):
                    raise PermissionError("MCP tools are disabled in tools config")
                result = self._mcp.call_tool(
                    str(args.get("server_id") or ""),
                    str(args.get("tool_name") or ""),
                    args.get("arguments") if isinstance(args.get("arguments"), dict) else {},
                )
            else:
                raise ValueError(f"Unknown tool: {name}")
            payload = {
                "ok": True,
                "tool": name,
                "result": result,
                "duration_seconds": round(time.time() - started, 3),
            }

            # Apply content filtering to results
            if hasattr(self, '_security') and self._security.get("content_filter"):
                content_filter = self._security["content_filter"]
                # Filter sensitive information from result if it contains text
                if isinstance(result, dict):
                    for key, value in result.items():
                        if isinstance(value, str) and len(value) > 0:
                            result[key] = content_filter.filter_output(value, user_id=user_id)

            self._event_log.add(
                "tool.run.success",
                "Tool execution succeeded",
                {"tool": name, "duration_seconds": payload["duration_seconds"], "user_id": user_id},
            )
            return payload
        except Exception as exc:
            payload = {
                "ok": False,
                "tool": name,
                "error": f"{exc.__class__.__name__}: {exc}",
                "duration_seconds": round(time.time() - started, 3),
            }
            self._event_log.add(
                "tool.run.error",
                "Tool execution failed",
                {"tool": name, "error": payload["error"], "trace": trace_details},
            )
            return payload
