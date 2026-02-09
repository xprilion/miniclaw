"""MCP (Model Context Protocol) stdio server session and manager."""
from __future__ import annotations

import copy
import json
import os
import select
import shlex
import subprocess
import time
from typing import Any, Dict, List, Optional

from ..core.config import ConfigStore
from ..core.events import EventLog


class MCPStdioSession:
    def __init__(self, server: Dict[str, Any]) -> None:
        self.server = copy.deepcopy(server)
        self._process: Optional[subprocess.Popen[Any]] = None
        self._next_id = 1

    def _build_command(self) -> List[str]:
        command = str(self.server.get("command") or "").strip()
        if not command:
            raise ValueError(f"MCP server {self.server.get('id')} has no command configured")
        args = [str(item) for item in self.server.get("args") or []]
        cmd_parts = shlex.split(command) if " " in command else [command]
        return cmd_parts + args

    def start(self) -> None:
        if self._process is not None:
            return
        timeout_seconds = max(5, int(self.server.get("timeout_seconds") or 30))
        _ = timeout_seconds  # keep for clarity in logs/callers
        cmd = self._build_command()
        cwd = str(self.server.get("cwd") or "").strip() or None
        env = os.environ.copy()
        server_env = self.server.get("env") or {}
        if isinstance(server_env, dict):
            for key, value in server_env.items():
                env[str(key)] = str(value)

        self._process = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            bufsize=0,
        )

    def stop(self) -> None:
        proc = self._process
        if proc is None:
            return
        try:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        finally:
            self._process = None

    def _stdout(self) -> Any:
        if self._process is None or self._process.stdout is None:
            raise RuntimeError("MCP process is not started")
        return self._process.stdout

    def _stdin(self) -> Any:
        if self._process is None or self._process.stdin is None:
            raise RuntimeError("MCP process is not started")
        return self._process.stdin

    def _read_message(self, timeout_seconds: int) -> Dict[str, Any]:
        stdout = self._stdout()
        deadline = time.time() + max(1, timeout_seconds)
        headers: Dict[str, str] = {}
        raw_line = b""
        while True:
            remaining = max(0.1, deadline - time.time())
            readable, _, _ = select.select([stdout], [], [], remaining)
            if not readable:
                raise TimeoutError("Timed out waiting for MCP response headers")
            raw_line = stdout.readline()
            if raw_line == b"":
                raise RuntimeError("MCP process closed stdout")
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                break
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()
            elif line.startswith("{") and line.endswith("}"):
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    return parsed
                raise RuntimeError("Unexpected MCP response payload")

        content_length_text = headers.get("content-length")
        if not content_length_text:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if line.startswith("{") and line.endswith("}"):
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    return parsed
            raise RuntimeError("Missing Content-Length in MCP response")
        content_length = int(content_length_text)
        payload = b""
        while len(payload) < content_length:
            remaining = max(0.1, deadline - time.time())
            readable, _, _ = select.select([stdout], [], [], remaining)
            if not readable:
                raise TimeoutError("Timed out waiting for MCP response body")
            chunk = stdout.read(content_length - len(payload))
            if not chunk:
                break
            payload += chunk
        if not payload:
            raise RuntimeError("MCP response payload is empty")
        decoded = payload.decode("utf-8", errors="replace")
        parsed = json.loads(decoded)
        if not isinstance(parsed, dict):
            raise RuntimeError("Unexpected MCP response object")
        return parsed

    def _send(self, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        stdin = self._stdin()
        stdin.write(header)
        stdin.write(body)
        stdin.flush()

    def notify(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }
        self._send(payload)

    def request(self, method: str, params: Optional[Dict[str, Any]] = None,
                timeout_seconds: int = 30) -> Dict[str, Any]:
        req_id = self._next_id
        self._next_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }
        self._send(payload)
        deadline = time.time() + max(1, timeout_seconds)
        while True:
            remaining = max(1, int(deadline - time.time()))
            message = self._read_message(timeout_seconds=remaining)
            if message.get("id") != req_id:
                continue
            if "error" in message:
                error = message.get("error")
                raise RuntimeError(f"MCP error for {method}: {error}")
            result = message.get("result")
            if isinstance(result, dict):
                return result
            return {"result": result}

    def initialize(self, timeout_seconds: int = 30) -> Dict[str, Any]:
        result = self.request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "MiniClaw", "version": "0.1"},
            },
            timeout_seconds=timeout_seconds,
        )
        try:
            self.notify("notifications/initialized", {})
        except Exception:
            # Some servers don't require/implement initialized notification.
            pass
        return result


class MCPServerManager:
    def __init__(self, config_store: ConfigStore, event_log: EventLog) -> None:
        self._config_store = config_store
        self._event_log = event_log

    def _config(self) -> Dict[str, Any]:
        return self._config_store.get().get("mcp") or {"enabled": True, "servers": []}

    def _servers(self) -> List[Dict[str, Any]]:
        mcp_cfg = self._config()
        servers = mcp_cfg.get("servers") or []
        if not isinstance(servers, list):
            return []
        return [copy.deepcopy(item) for item in servers if isinstance(item, dict)]

    def list_servers(self) -> List[Dict[str, Any]]:
        return self._servers()

    def _find_server(self, server_id: str) -> Dict[str, Any]:
        wanted = str(server_id or "").strip().lower()
        for server in self._servers():
            if str(server.get("id") or "").strip().lower() == wanted:
                return server
        raise ValueError(f"MCP server not found: {wanted}")

    def _session_for(self, server_id: str) -> MCPStdioSession:
        server = self._find_server(server_id)
        if not bool(server.get("enabled", True)):
            raise ValueError(f"MCP server is disabled: {server_id}")
        transport = str(server.get("transport") or "stdio").strip().lower()
        if transport != "stdio":
            raise ValueError(f"Unsupported MCP transport: {transport}")
        if not str(server.get("command") or "").strip():
            raise ValueError(f"MCP server command is empty: {server_id}")
        return MCPStdioSession(server)

    def test_server(self, server_id: str) -> Dict[str, Any]:
        session = self._session_for(server_id)
        started = time.time()
        try:
            session.start()
            init = session.initialize(timeout_seconds=int(session.server.get("timeout_seconds") or 30))
            result = {
                "ok": True,
                "server_id": server_id,
                "duration_seconds": round(time.time() - started, 3),
                "initialize": init,
            }
            self._event_log.add(
                "mcp.test.success",
                "MCP server test succeeded",
                {"server_id": server_id, "duration_seconds": result["duration_seconds"]},
            )
            return result
        except Exception as exc:
            self._event_log.add(
                "mcp.test.error",
                "MCP server test failed",
                {"server_id": server_id, "error": f"{exc.__class__.__name__}: {exc}"},
            )
            raise
        finally:
            session.stop()

    def list_tools(self, server_id: str) -> Dict[str, Any]:
        session = self._session_for(server_id)
        try:
            session.start()
            session.initialize(timeout_seconds=int(session.server.get("timeout_seconds") or 30))
            tools_result = session.request("tools/list", {},
                                           timeout_seconds=int(session.server.get("timeout_seconds") or 30))
            tools = tools_result.get("tools")
            if not isinstance(tools, list):
                tools = []
            result = {
                "server_id": server_id,
                "tools": tools,
                "count": len(tools),
            }
            self._event_log.add(
                "mcp.tools.list",
                "Listed MCP tools",
                {"server_id": server_id, "count": len(tools)},
            )
            return result
        finally:
            session.stop()

    def call_tool(self, server_id: str, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        name = str(tool_name or "").strip()
        if not name:
            raise ValueError("tool_name is required")
        args = arguments if isinstance(arguments, dict) else {}
        session = self._session_for(server_id)
        try:
            session.start()
            session.initialize(timeout_seconds=int(session.server.get("timeout_seconds") or 30))
            result = session.request(
                "tools/call",
                {"name": name, "arguments": args},
                timeout_seconds=int(session.server.get("timeout_seconds") or 30),
            )
            payload = {
                "server_id": server_id,
                "tool_name": name,
                "result": result,
            }
            self._event_log.add(
                "mcp.tools.call",
                "Called MCP tool",
                {"server_id": server_id, "tool_name": name},
            )
            return payload
        finally:
            session.stop()
