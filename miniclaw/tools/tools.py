"""Agent tools: shell, filesystem, fetch, browser, MCP, search, jobs."""
from __future__ import annotations

import copy
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.app_state import AppState

from ..core.config import ConfigStore
from ..core.events import EventLog
from ..services.mcp import MCPServerManager
from ..core.parser import HTMLTextExtractor
from ..security.security import SandboxManager
from ..core.util import extract_json_object, truncate_text
from .brave_search import BraveSearchClient


class ToolRunner:
    """Agent tools: shell, filesystem, fetch, browser, MCP, search, jobs."""

    def __init__(self, config_store: ConfigStore, event_log: EventLog, mcp: MCPServerManager,
                 security_managers: Optional[Dict[str, Any]] = None, app_state: Optional['AppState'] = None) -> None:
        self._config_store = config_store
        self._event_log = event_log
        self._mcp = mcp
        self._security_managers = security_managers or {}
        self._app_state = app_state
        self._sandbox = SandboxManager(config_store, event_log)
        self._brave_search_client: Optional[BraveSearchClient] = None
        # Initialize source tracking attributes
        self._current_source: Optional[str] = None
        self._current_meta: Dict[str, Any] = {}
        self._current_chat_id: Optional[str] = None
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
                "name": "brave_search",
                "description": "Search the web using Brave Search API for current information.",
                "args_schema": {
                    "query": "string", 
                    "count": "int(optional, default=5)", 
                    "country": "string(optional, default='us')", 
                    "search_lang": "string(optional, default='en')"
                },
            },
            {
                "name": "jobs_create",
                "description": "Create or update a scheduled job that runs periodically. To stop/disable a job, set enabled=false rather than deleting it.",
                "args_schema": {
                    "id": "string", 
                    "name": "string", 
                    "prompt": "string",
                    "interval_seconds": "int(optional, default=300)",
                    "enabled": "boolean(optional, default=true)",
                    "send_to_telegram_chat_id": "string(optional)"
                },
            },
            {
                "name": "jobs_list",
                "description": "List all scheduled jobs.",
                "args_schema": {},
            },
            {
                "name": "jobs_delete",
                "description": "Delete a scheduled job by ID. Prefer disabling jobs (set enabled=false in jobs_create) rather than deleting to preserve configuration.",
                "args_schema": {"id": "string"},
            },
            {
                "name": "jobs_toggle",
                "description": "Toggle a job between enabled and disabled states. Preferred way to temporarily stop/start jobs.",
                "args_schema": {
                    "id": "string"
                },
            },
            {
                "name": "jobs_run",
                "description": "Manually trigger a job to run immediately.",
                "args_schema": {"id": "string"},
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

    def _init_brave_search_client(self) -> BraveSearchClient:
        """Initialize Brave Search client with API key from config."""
        if self._brave_search_client is not None:
            return self._brave_search_client
            
        config = self._cfg()
        api_key = config.get("brave_search", {}).get("api_key")
        if not api_key:
            raise PermissionError("Brave Search API key not configured in tools config")
            
        self._brave_search_client = BraveSearchClient(api_key)
        return self._brave_search_client

    def _brave_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform web search using Brave Search API.
        
        Args:
            arguments: Tool arguments containing query and optional parameters
            
        Returns:
            Dictionary with search results
        """
        # Validate arguments
        query = arguments.get("query")
        if not query:
            raise ValueError("Search query is required")
        
        # Get optional parameters with defaults
        count = arguments.get("count", 5)
        country = arguments.get("country", "us")
        search_lang = arguments.get("search_lang", "en")
        
        # Initialize Brave Search client
        try:
            client = self._init_brave_search_client()
        except PermissionError as e:
            raise PermissionError(f"Brave Search is not available: {str(e)}")
        
        # Perform search
        try:
            search_results = client.search(
                query=query,
                count=count,
                country=country,
                search_lang=search_lang
            )
            
            # Format results
            formatted_results = client.format_results(search_results)
            
            return {
                "results": formatted_results,
                "total_results": len(formatted_results),
                "query": query
            }
        except Exception as e:
            raise Exception(f"Brave Search failed: {str(e)}")

    def _jobs_create(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or update a scheduled job.
        
        Args:
            arguments: Tool arguments for job creation
            
        Returns:
            Dictionary with job creation result
        """
        if self._app_state is None:
            raise PermissionError("Job management not available - app_state not provided")
            
        # Validate required arguments
        job_id = str(arguments.get("id", "")).strip()
        name = str(arguments.get("name", "")).strip()
        prompt = str(arguments.get("prompt", "")).strip()
        
        if not job_id:
            raise ValueError("Job ID is required")
        if not name:
            raise ValueError("Job name is required")
        if not prompt:
            raise ValueError("Job prompt is required")
            
        # Get optional parameters with defaults
        interval_seconds = int(arguments.get("interval_seconds", 300))
        enabled = bool(arguments.get("enabled", True))
        send_to_telegram_chat_id = str(arguments.get("send_to_telegram_chat_id", "")).strip()
        
        # If no chat ID was provided but we're in a Telegram context, 
        # automatically set it to the requesting chat ID
        if not send_to_telegram_chat_id and hasattr(self, '_current_chat_id'):
            send_to_telegram_chat_id = self._current_chat_id
            
        # Create job payload
        job_payload = {
            "id": job_id,
            "name": name,
            "prompt": prompt,
            "interval_seconds": interval_seconds,
            "enabled": enabled,
            "send_to_telegram_chat_id": send_to_telegram_chat_id,
        }
        
        try:
            # Use the app_state's upsert_job method
            created_job = self._app_state.upsert_job(job_payload)
            return {
                "success": True,
                "message": f"Job '{name}' ({job_id}) created/updated successfully",
                "job": created_job
            }
        except Exception as e:
            raise Exception(f"Failed to create job: {str(e)}")

    def _jobs_list(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        List all scheduled jobs.
        
        Args:
            arguments: Tool arguments (empty for this tool)
            
        Returns:
            Dictionary with list of jobs
        """
        if self._app_state is None:
            raise PermissionError("Job management not available - app_state not provided")
            
        try:
            # Use the app_state's job_store to list jobs
            jobs = self._app_state.job_store.list()
            return {
                "success": True,
                "jobs": jobs,
                "count": len(jobs)
            }
        except Exception as e:
            raise Exception(f"Failed to list jobs: {str(e)}")

    def _jobs_delete(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delete a scheduled job.
        
        Args:
            arguments: Tool arguments containing job ID
            
        Returns:
            Dictionary with deletion result
        """
        if self._app_state is None:
            raise PermissionError("Job management not available - app_state not provided")
            
        # Validate required argument
        job_id = str(arguments.get("id", "")).strip()
        if not job_id:
            raise ValueError("Job ID is required")
            
        try:
            # Use the app_state's delete_job method
            self._app_state.delete_job(job_id)
            return {
                "success": True,
                "message": f"Job '{job_id}' deleted successfully"
            }
        except Exception as e:
            raise Exception(f"Failed to delete job: {str(e)}")

    def _jobs_toggle(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Toggle a job between enabled and disabled states.
        
        Args:
            arguments: Tool arguments containing job ID
            
        Returns:
            Dictionary with toggle result
        """
        if self._app_state is None:
            raise PermissionError("Job management not available - app_state not provided")
            
        # Validate required argument
        job_id = str(arguments.get("id", "")).strip()
        if not job_id:
            raise ValueError("Job ID is required")
            
        try:
            # Get the current job to see its state
            current_job = None
            jobs = self._app_state.job_store.list()
            for job in jobs:
                if job.get("id") == job_id:
                    current_job = job
                    break
                    
            if current_job is None:
                raise ValueError(f"Job '{job_id}' not found")
                
            # Toggle the enabled state
            new_enabled_state = not bool(current_job.get("enabled", True))
            
            # Update the job with the new state
            job_payload = {
                "id": job_id,
                "name": current_job.get("name", job_id),
                "prompt": current_job.get("prompt", ""),
                "interval_seconds": current_job.get("interval_seconds", 300),
                "enabled": new_enabled_state,
                "send_to_telegram_chat_id": current_job.get("send_to_telegram_chat_id", ""),
            }
            
            # Use the app_state's upsert_job method
            updated_job = self._app_state.upsert_job(job_payload)
            state_text = "enabled" if new_enabled_state else "disabled"
            
            return {
                "success": True,
                "message": f"Job '{job_id}' has been {state_text}",
                "job": updated_job,
                "previous_state": "enabled" if not new_enabled_state else "disabled",
                "new_state": state_text
            }
        except Exception as e:
            raise Exception(f"Failed to toggle job: {str(e)}")

    def _jobs_run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manually trigger a job to run.
        
        Args:
            arguments: Tool arguments containing job ID
            
        Returns:
            Dictionary with run result
        """
        if self._app_state is None:
            raise PermissionError("Job management not available - app_state not provided")
            
        # Validate required argument
        job_id = str(arguments.get("id", "")).strip()
        if not job_id:
            raise ValueError("Job ID is required")
            
        try:
            # Use the app_state's job_service to trigger the job
            result = self._app_state.job_service.trigger_now(job_id)
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            raise Exception(f"Failed to run job: {str(e)}")

    def run(self, tool_name: str, arguments: Optional[Dict[str, Any]],
            trace: Optional[Dict[str, Any]] = None, user_id: str = "default") -> Dict[str, Any]:
        name = str(tool_name or "").strip()
        args = arguments if isinstance(arguments, dict) else {}
        trace_details = trace if isinstance(trace, dict) else {}
        started = time.time()

        # Store source information for tools that need it (e.g., jobs_create)
        source = trace_details.get("source", "unknown")
        self._current_source = source
        self._current_meta = trace_details.get("meta", {})
        if source == "telegram" and "chat_id" in self._current_meta:
            self._current_chat_id = self._current_meta["chat_id"]
        else:
            self._current_chat_id = None

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
                if not self._allow("allow_browser", True):
                    raise PermissionError("browser_extract is disabled in tools config")
                result = self._browser_extract(args)
            elif name == "brave_search":
                if not self._allow("allow_network", True):
                    raise PermissionError("brave_search is disabled in tools config")
                result = self._brave_search(args)
            elif name == "jobs_create":
                if not self._allow("allow_network", True):
                    raise PermissionError("jobs_create is disabled in tools config")
                result = self._jobs_create(args)
            elif name == "jobs_list":
                if not self._allow("allow_network", True):
                    raise PermissionError("jobs_list is disabled in tools config")
                result = self._jobs_list(args)
            elif name == "jobs_delete":
                if not self._allow("allow_network", True):
                    raise PermissionError("jobs_delete is disabled in tools config")
                result = self._jobs_delete(args)
            elif name == "jobs_toggle":
                if not self._allow("allow_network", True):
                    raise PermissionError("jobs_toggle is disabled in tools config")
                result = self._jobs_toggle(args)
            elif name == "jobs_run":
                if not self._allow("allow_network", True):
                    raise PermissionError("jobs_run is disabled in tools config")
                result = self._jobs_run(args)
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
