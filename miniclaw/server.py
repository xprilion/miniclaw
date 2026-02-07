"""HTTP server and request routing."""
from __future__ import annotations

import json
import mimetypes
import os
import ssl
import traceback
import urllib.parse
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

from .constants import WEB_DIR, LEGACY_WEB_DIR, WEB_ROUTES
from .app_state import AppState
from .util import LOGGER, utc_now

def make_handler(state: AppState):
    class MiniClawHandler(BaseHTTPRequestHandler):
        server_version = "MiniClaw/0.1"

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _read_body(self) -> str:
            raw_length = self.headers.get("Content-Length")
            length = int(raw_length) if raw_length else 0
            if length <= 0:
                return ""
            return self.rfile.read(length).decode("utf-8", errors="replace")

        def _read_json(self) -> Dict[str, Any]:
            text = self._read_body()
            if not text.strip():
                return {}
            parsed = json.loads(text)
            if not isinstance(parsed, dict):
                raise ValueError("Request body must be a JSON object")
            return parsed

        def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
            text = json.dumps(payload, indent=2, sort_keys=True)
            data = text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_text(self, text: str, status: int = 200, content_type: str = "text/plain; charset=utf-8") -> None:
            data = text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _serve_web_file(self, filename: str) -> None:
            target = (WEB_DIR / filename).resolve()
            
            # If file doesn't exist in new frontend, try legacy frontend
            if not target.exists() or not target.is_file():
                legacy_target = (LEGACY_WEB_DIR / filename).resolve()
                if legacy_target.exists() and legacy_target.is_file():
                    target = legacy_target
            
            try:
                target.relative_to(WEB_DIR.resolve() if target.is_relative_to(WEB_DIR.resolve()) else LEGACY_WEB_DIR.resolve())
            except ValueError:
                self._send_text("Forbidden", status=403)
                return

            if not target.exists() or not target.is_file():
                self._send_text(f"Missing web asset: {filename}", status=404)
                return

            raw = target.read_bytes()
            content_type, _ = mimetypes.guess_type(str(target))
            if not content_type:
                content_type = "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8" if content_type.startswith("text/") else content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _handle_error(self, exc: Exception, path: str) -> None:
            state.event_log.add(
                "http.error",
                "HTTP request failed",
                {
                    "method": self.command,
                    "path": path,
                    "error": f"{exc.__class__.__name__}: {exc}",
                    "traceback": traceback.format_exc(limit=10),
                },
            )
            self._send_json(
                {
                    "ok": False,
                    "error": f"{exc.__class__.__name__}: {exc}",
                },
                status=500,
            )

        def _handle_openai_proxy(self) -> None:
            """Handle OpenAI-compatible API requests and proxy them to configured providers."""
            # Read the request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else b''
            
            # Get the authorization header
            auth_header = self.headers.get('Authorization', '')
            content_type = self.headers.get('Content-Type', 'application/json')
            
            # Try to parse the request to determine which provider to use
            try:
                if post_data:
                    payload = json.loads(post_data.decode('utf-8'))
                else:
                    payload = {}
            except json.JSONDecodeError:
                payload = {}
            
            # Get the model from the request
            model = payload.get('model', '')
            
            # Find the appropriate provider based on the model or use default
            provider = None
            if model:
                # Try to find a provider that matches this model
                for p in state.config_store.get().get('providers', {}).get('items', []):
                    if p.get('model', '') == model and p.get('enabled', False):
                        provider = p
                        break
            
            # If no specific model match, use the default provider
            if not provider:
                default_provider_id = state.config_store.get().get('providers', {}).get('default_provider_id')
                for p in state.config_store.get().get('providers', {}).get('items', []):
                    if p.get('id') == default_provider_id and p.get('enabled', False):
                        provider = p
                        break
            
            # If still no provider, use the first enabled provider
            if not provider:
                for p in state.config_store.get().get('providers', {}).get('items', []):
                    if p.get('enabled', False):
                        provider = p
                        break
            
            if not provider:
                self._send_json({"ok": False, "error": "No enabled provider found"}, status=500)
                return
            
            # Forward the request to the provider
            provider_type = provider.get('type', 'ollama')
            base_url = provider.get('base_url', '').rstrip('/')
            api_key = provider.get('api_key', '')
            
            # Construct the target URL
            if self.path.startswith('/v1/'):
                # This is a direct OpenAI API path
                target_path = self.path
            else:
                target_path = '/chat/completions'  # default
                
            target_url = f"{base_url}{target_path}"
            
            # Prepare headers for forwarding
            headers = {
                'Content-Type': content_type,
                'Accept': 'application/json',
            }
            
            # Add authorization if available
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
            
            # Add any other headers that might be needed
            if provider_type == 'openrouter':
                headers['HTTP-Referer'] = 'https://miniclaw.ai'
                headers['X-Title'] = 'MiniClaw'
            
            # Create the request
            req = urllib.request.Request(
                url=target_url,
                data=post_data,
                headers=headers,
                method='POST'
            )
            
            # Handle SSL context
            ssl_context = None
            if target_url.startswith('https://') and not provider.get('verify_tls', True):
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            
            try:
                # Forward the request
                with urllib.request.urlopen(req, timeout=provider.get('timeout_seconds', 300), context=ssl_context) as response:
                    # Read and forward the response
                    response_data = response.read()
                    self.send_response(response.status)
                    
                    # Forward response headers
                    for header_name, header_value in response.headers.items():
                        # Skip headers that shouldn't be forwarded
                        if header_name.lower() not in ['connection', 'transfer-encoding']:
                            self.send_header(header_name, header_value)
                    
                    self.end_headers()
                    self.wfile.write(response_data)
                    
            except urllib.error.HTTPError as e:
                # Forward HTTP errors
                self.send_response(e.code)
                # Forward error headers
                for header_name, header_value in e.headers.items():
                    if header_name.lower() not in ['connection', 'transfer-encoding']:
                        self.send_header(header_name, header_value)
                self.end_headers()
                self.wfile.write(e.read())
                
            except Exception as e:
                # Handle other errors
                self._send_json({"ok": False, "error": f"Proxy error: {str(e)}"}, status=500)

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            query = urllib.parse.parse_qs(parsed.query)
            LOGGER.debug("HTTP GET %s", path)

            if path != "/api/events":
                state.event_log.add(
                    "http.request",
                    "Incoming HTTP request",
                    {
                        "method": "GET",
                        "path": path,
                        "query": query,
                    },
                )

            try:
                if path in WEB_ROUTES:
                    self._serve_web_file(WEB_ROUTES[path])
                    return
                if path.startswith("/static/"):
                    relative = path[len("/static/") :]
                    if not relative:
                        self._send_text("Missing static file path", status=404)
                        return
                    self._serve_web_file(relative)
                    return
                if path == "/favicon.ico":
                    self.send_response(204)
                    self.end_headers()
                    return
                if path == "/api/health":
                    self._send_json({"ok": True, "timestamp": utc_now()})
                    return
                if path == "/api/config":
                    self._send_json({"ok": True, "config": state.config_store.get()})
                    return
                if path == "/api/config/raw":
                    self._send_json(
                        {
                            "ok": True,
                            "path": str(state.config_store.path),
                            "raw": state.config_store.raw_text(),
                        }
                    )
                    return
                if path == "/api/models":
                    provider_id = str((query.get("provider_id") or [""])[0] or "").strip()
                    try:
                        resolved = state.list_models(provider_id=provider_id)
                    except ValueError as exc:
                        self._send_json({"ok": False, "error": str(exc)}, status=400)
                        return
                    self._send_json({"ok": True, "models": resolved["models"], "provider": resolved["provider"]})
                    return
                if path == "/api/usage":
                    limit = int((query.get("limit") or [250])[0])
                    usage = state.usage_snapshot(limit=limit)
                    self._send_json({"ok": True, "usage": usage})
                    return
                if path == "/api/memory":
                    name = str((query.get("name") or [""])[0] or "").strip()
                    if name:
                        try:
                            memory_file = state.memory.read(name)
                        except ValueError as exc:
                            self._send_json({"ok": False, "error": str(exc)}, status=400)
                            return
                        self._send_json({"ok": True, "file": memory_file, "files": state.memory.list_files()})
                        return
                    self._send_json({"ok": True, "files": state.memory.read_all(), "config": state.config_store.get().get("memory")})
                    return
                if path == "/api/skills":
                    self._send_json({"ok": True, "skills": state.skills.list()})
                    return
                if path == "/api/plugins":
                    self._send_json({"ok": True, "plugins": state.plugins.list()})
                    return
                if path == "/api/runtime":
                    self._send_json({"ok": True, "runtime": state.runtime_snapshot()})
                    return
                if path == "/api/tools":
                    catalog = state.tools.catalog(include_mcp_details=True)
                    self._send_json({"ok": True, "tools": catalog})
                    return
                if path == "/api/scheduler":
                    self._send_json({"ok": True, "scheduler": state.scheduler.status()})
                    return
                if path == "/api/telegram/pairings":
                    self._send_json({"ok": True, "pairings": state.telegram.pairing_status()})
                    return
                if path == "/api/history":
                    limit = int((query.get("limit") or [100])[0])
                    self._send_json({"ok": True, "history": state.agent.history(limit=limit)})
                    return
                if path == "/api/events":
                    since_id = int((query.get("since_id") or [0])[0])
                    limit = int((query.get("limit") or [200])[0])
                    events = state.event_log.list_since(since_id=since_id, limit=limit)
                    self._send_json(
                        {
                            "ok": True,
                            "events": events,
                            "latest_id": state.event_log.latest_id(),
                        }
                    )
                    return

                self._send_json({"ok": False, "error": f"Unknown endpoint: {path}"}, status=404)
            except Exception as exc:
                self._handle_error(exc, path)

        def do_POST(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            LOGGER.debug("HTTP POST %s", path)
            state.event_log.add(
                "http.request",
                "Incoming HTTP request",
                {
                    "method": "POST",
                    "path": path,
                },
            )

            try:
                # Handle OpenAI-compatible proxy requests to W&B Inference
                if path == "/v1/chat/completions" or path.startswith("/v1/"):
                    # This is an OpenAI-compatible API request
                    # Forward it to the configured provider or W&B Inference
                    return self._handle_openai_proxy()

                if path == "/api/chat":
                    payload = self._read_json()
                    message = str(payload.get("message") or "").strip()
                    source = str(payload.get("source") or "web")
                    provider_id = str(payload.get("provider_id") or "").strip()
                    if not message:
                        self._send_json({"ok": False, "error": "message is required"}, status=400)
                        return
                    result = state.agent.chat(
                        message,
                        source=source,
                        meta={
                            "client_ip": self.client_address[0],
                            "provider_id": provider_id,
                        },
                    )
                    self._send_json({"ok": True, **result})
                    return

                if path == "/api/memory/save":
                    payload = self._read_json()
                    name = str(payload.get("name") or "").strip()
                    content = str(payload.get("content") or "")
                    if not name:
                        self._send_json({"ok": False, "error": "name is required"}, status=400)
                        return
                    try:
                        saved = state.memory.save(name=name, content=content)
                    except ValueError as exc:
                        self._send_json({"ok": False, "error": str(exc)}, status=400)
                        return
                    self._send_json({"ok": True, "file": saved, "files": state.memory.list_files()})
                    return

                if path == "/api/telegram/restart":
                    restarted = state.telegram.restart()
                    self._send_json({"ok": True, "restarted": restarted, "telegram": state.telegram.status()})
                    return

                if path == "/api/telegram/test":
                    payload = self._read_json()
                    chat_id = str(payload.get("chat_id") or "").strip()
                    message = str(payload.get("message") or "MiniClaw test message")
                    if not chat_id:
                        self._send_json({"ok": False, "error": "chat_id is required"}, status=400)
                        return
                    state.telegram.send_test_message(chat_id=chat_id, message=message)
                    self._send_json({"ok": True})
                    return

                if path == "/api/telegram/unbind":
                    result = state.telegram.unbind_chat(actor="api")
                    self._send_json({"ok": True, "result": result, "telegram": state.telegram.status()})
                    return

                if path == "/api/telegram/pairing/start":
                    payload = self._read_json()
                    ttl_seconds = payload.get("ttl_seconds")
                    try:
                        pairing = state.telegram.create_pairing_code(ttl_seconds=ttl_seconds)
                    except ValueError as exc:
                        self._send_json({"ok": False, "error": str(exc)}, status=400)
                        return
                    self._send_json({"ok": True, "pairing": pairing})
                    return

                if path == "/api/telegram/pairing/confirm":
                    payload = self._read_json()
                    request_id = str(payload.get("request_id") or "").strip()
                    if not request_id:
                        self._send_json({"ok": False, "error": "request_id is required"}, status=400)
                        return
                    try:
                        resolved = state.telegram.resolve_pairing_request(request_id, approve=True, actor="api")
                    except ValueError as exc:
                        self._send_json({"ok": False, "error": str(exc)}, status=400)
                        return
                    self._send_json({"ok": True, "request": resolved})
                    return

                if path == "/api/telegram/pairing/reject":
                    payload = self._read_json()
                    request_id = str(payload.get("request_id") or "").strip()
                    if not request_id:
                        self._send_json({"ok": False, "error": "request_id is required"}, status=400)
                        return
                    try:
                        resolved = state.telegram.resolve_pairing_request(request_id, approve=False, actor="api")
                    except ValueError as exc:
                        self._send_json({"ok": False, "error": str(exc)}, status=400)
                        return
                    self._send_json({"ok": True, "request": resolved})
                    return

                if path == "/api/skills/save":
                    payload = self._read_json()
                    skill_id = str(payload.get("id") or "").strip()
                    content = str(payload.get("content") or "")
                    if not skill_id:
                        self._send_json({"ok": False, "error": "id is required"}, status=400)
                        return
                    if not content.strip():
                        self._send_json({"ok": False, "error": "content is required"}, status=400)
                        return
                    try:
                        saved = state.skills.save_markdown_skill(skill_id, content)
                    except ValueError as exc:
                        self._send_json({"ok": False, "error": str(exc)}, status=400)
                        return
                    self._send_json({"ok": True, "skill": saved, "skills": state.skills.list()})
                    return

                if path == "/api/skills/delete":
                    payload = self._read_json()
                    skill_id = str(payload.get("id") or "").strip()
                    if not skill_id:
                        self._send_json({"ok": False, "error": "id is required"}, status=400)
                        return
                    try:
                        deleted = state.skills.delete_skill(skill_id)
                    except ValueError as exc:
                        self._send_json({"ok": False, "error": str(exc)}, status=400)
                        return
                    self._send_json({"ok": True, "deleted": deleted, "skills": state.skills.list()})
                    return

                if path == "/api/skills/settings":
                    payload = self._read_json()
                    enabled_skills = payload.get("enabled_skills") or []
                    if not isinstance(enabled_skills, list):
                        self._send_json({"ok": False, "error": "enabled_skills must be a list"}, status=400)
                        return
                    min_score = int(payload.get("skill_match_min_score") or 2)
                    settings = state.update_skill_settings(enabled_skills, min_score=min_score)
                    self._send_json({"ok": True, "settings": settings})
                    return

                if path == "/api/scheduler/upsert":
                    payload = self._read_json()
                    try:
                        job = state.upsert_scheduler_job(payload)
                    except ValueError as exc:
                        self._send_json({"ok": False, "error": str(exc)}, status=400)
                        return
                    self._send_json({"ok": True, "job": job, "scheduler": state.scheduler.status()})
                    return

                if path == "/api/scheduler/delete":
                    payload = self._read_json()
                    job_id = str(payload.get("id") or "").strip()
                    if not job_id:
                        self._send_json({"ok": False, "error": "id is required"}, status=400)
                        return
                    try:
                        deleted = state.delete_scheduler_job(job_id)
                    except ValueError as exc:
                        self._send_json({"ok": False, "error": str(exc)}, status=400)
                        return
                    self._send_json({"ok": True, "deleted": deleted, "scheduler": state.scheduler.status()})
                    return

                if path == "/api/scheduler/run":
                    payload = self._read_json()
                    job_id = str(payload.get("id") or "").strip()
                    if not job_id:
                        self._send_json({"ok": False, "error": "id is required"}, status=400)
                        return
                    try:
                        result = state.scheduler.trigger_now(job_id)
                    except ValueError as exc:
                        self._send_json({"ok": False, "error": str(exc)}, status=400)
                        return
                    self._send_json({"ok": True, "result": result, "scheduler": state.scheduler.status()})
                    return

                if path == "/api/tools/run":
                    payload = self._read_json()
                    tool_name = str(payload.get("tool") or "").strip()
                    tool_args = payload.get("arguments") if isinstance(payload.get("arguments"), dict) else {}
                    if not tool_name:
                        self._send_json({"ok": False, "error": "tool is required"}, status=400)
                        return
                    try:
                        run_result = state.tools.run(tool_name, tool_args)
                        self._send_json({"ok": True, "result": run_result})
                    except Exception as exc:
                        self._send_json({
                            "ok": False,
                            "error": str(exc),
                            "result": {"ok": False, "tool": tool_name, "error": f"{exc.__class__.__name__}: {exc}"},
                        }, status=200)
                    return
                if path == "/api/mcp/test":
                    payload = self._read_json()
                    server_id = str(payload.get("server_id") or "").strip()
                    if not server_id:
                        self._send_json({"ok": False, "error": "server_id is required"}, status=400)
                        return
                    try:
                        result = state.mcp.test_server(server_id)
                        self._send_json({
                            "ok": True,
                            "success": result.get("ok", False),
                            "message": f"Server responded in {result.get('duration_seconds', 0)}s",
                            "error": None,
                        })
                    except Exception as exc:
                        self._send_json({
                            "ok": True,
                            "success": False,
                            "message": "",
                            "error": str(exc),
                        })
                    return
                if path == "/api/plugins/reload":
                    state.plugins.reload()
                    enabled = state.config_store.get()["agent"].get("enabled_plugins") or []
                    state.plugins.set_enabled(enabled)
                    self._send_json({"ok": True, "plugins": state.plugins.list()})
                    return

                self._send_json({"ok": False, "error": f"Unknown endpoint: {path}"}, status=404)
            except Exception as exc:
                self._handle_error(exc, path)

        def do_PUT(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            LOGGER.debug("HTTP PUT %s", path)
            state.event_log.add(
                "http.request",
                "Incoming HTTP request",
                {
                    "method": "PUT",
                    "path": path,
                },
            )

            try:
                if path == "/api/config":
                    payload = self._read_json()
                    updated = state.apply_config(payload)
                    self._send_json({"ok": True, "config": updated})
                    return

                if path == "/api/config/raw":
                    content_type = self.headers.get("Content-Type") or ""
                    if "application/json" in content_type:
                        payload = self._read_json()
                        raw = str(payload.get("raw") or "")
                    else:
                        raw = self._read_body()
                    updated = state.apply_raw_config(raw)
                    self._send_json({"ok": True, "config": updated})
                    return

                self._send_json({"ok": False, "error": f"Unknown endpoint: {path}"}, status=404)
            except json.JSONDecodeError as exc:
                self._send_json({"ok": False, "error": f"Invalid JSON: {exc}"}, status=400)
            except Exception as exc:
                self._handle_error(exc, path)

    return MiniClawHandler