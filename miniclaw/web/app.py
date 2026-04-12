"""FastAPI web application for MiniClaw."""
from __future__ import annotations

import asyncio
import json
import mimetypes
import ssl
import time
import traceback
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTasks

from ..core.app_state import AppState
from ..core.util import LOGGER, utc_now


def create_app(state: AppState) -> FastAPI:
    app = FastAPI(title="MiniClaw", docs_url=None, redoc_url=None)
    
    templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
    
    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request):
        return templates.TemplateResponse(
            "monitoring.html",
            {"request": request, "app_state": state}
        )
    
    @app.get("/monitoring", response_class=HTMLResponse)
    async def monitoring(request: Request):
        return templates.TemplateResponse(
            "monitoring.html",
            {"request": request, "app_state": state}
        )
    
    @app.get("/api/health")
    async def health():
        return {"ok": True, "timestamp": utc_now()}
    
    @app.get("/api/config")
    async def get_config():
        return {"ok": True, "config": state.config_store.get()}
    
    @app.get("/api/config/raw")
    async def get_config_raw():
        return {
            "ok": True,
            "path": str(state.config_store.path),
            "raw": state.config_store.raw_text(),
        }
    
    @app.put("/api/config")
    async def update_config(payload: Dict[str, Any]):
        updated = state.apply_config(payload)
        return {"ok": True, "config": updated}
    
    @app.put("/api/config/raw")
    async def update_config_raw(request: Request):
        content_type = request.headers.get("Content-Type", "")
        if "application/json" in content_type:
            body = await request.json()
            raw = str(body.get("raw") or "")
        else:
            raw = await request.body()
        updated = state.apply_raw_config(raw)
        return {"ok": True, "config": updated}
    
    @app.get("/api/models")
    async def list_models(provider_id: str = ""):
        try:
            resolved = state.list_models(provider_id=provider_id)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        return {"ok": True, "models": resolved["models"], "provider": resolved["provider"]}
    
    @app.get("/api/usage")
    async def get_usage(limit: int = 250):
        usage = state.usage_snapshot(limit=limit)
        return {"ok": True, "usage": usage}
    
    @app.get("/api/memory")
    async def get_memory(name: str = ""):
        if name:
            try:
                memory_file = state.memory.read(name)
            except ValueError as exc:
                return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
            return {"ok": True, "file": memory_file, "files": state.memory.list_files()}
        return {"ok": True, "files": state.memory.read_all(), "config": state.config_store.get().get("memory")}
    
    @app.get("/api/skills")
    async def list_skills():
        return {"ok": True, "skills": state.skills.list()}
    
    @app.get("/api/plugins")
    async def list_plugins():
        return {"ok": True, "plugins": state.plugins.list()}
    
    @app.get("/api/runtime")
    async def get_runtime():
        return {"ok": True, "runtime": state.runtime_snapshot()}
    
    @app.get("/api/tools")
    async def list_tools():
        catalog = state.tools.catalog(include_mcp_details=True)
        return {"ok": True, "tools": catalog}
    
    @app.get("/api/jobs")
    async def list_jobs():
        return {"ok": True, "jobs": state.job_service.status()}
    
    @app.get("/api/telegram/pairings")
    async def get_telegram_pairings():
        return {"ok": True, "pairings": state.telegram.pairing_status()}
    
    @app.get("/api/sessions")
    async def list_sessions():
        sessions = state.agent.list_sessions()
        return {"ok": True, "sessions": sessions}
    
    @app.get("/api/history")
    async def get_history(limit: int = 100, session_id: str = ""):
        if session_id:
            history = state.agent.history_for_session(session_id, limit=limit)
        else:
            history = state.agent.history(limit=limit)
        return {"ok": True, "history": history}
    
    @app.get("/api/events")
    async def get_events(since_id: int = 0, limit: int = 200):
        events = state.event_log.list_since(since_id=since_id, limit=limit)
        return {
            "ok": True,
            "events": events,
            "latest_id": state.event_log.latest_id(),
        }
    
    @app.get("/api/events/stream")
    async def events_stream(since_id: int = 0):
        async def event_generator():
            last_event_id = since_id
            try:
                yield f"data: {json.dumps({'type': 'connected', 'since_id': since_id})}\n\n"
                
                while True:
                    latest_id = state.event_log.latest_id()
                    if latest_id > last_event_id:
                        events = state.event_log.list_since(since_id=last_event_id, limit=50)
                        for event in events:
                            yield f"data: {json.dumps(event)}\n\n"
                            last_event_id = event.get("id", last_event_id + 1)
                    await asyncio.sleep(1)
            except Exception:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Stream ended'})}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
    
    @app.post("/api/chat")
    async def chat(payload: Dict[str, Any]):
        message = str(payload.get("message") or "").strip()
        source = str(payload.get("source") or "web")
        provider_id = str(payload.get("provider_id") or "").strip()
        stream = bool(payload.get("stream") or False)
        
        if not message:
            return JSONResponse({"ok": False, "error": "message is required"}, status_code=400)
        
        result = state.agent.chat(
            message,
            source=source,
            meta={"provider_id": provider_id},
        )
        return {"ok": True, **result}
    
    @app.post("/api/memory/save")
    async def save_memory(payload: Dict[str, Any]):
        name = str(payload.get("name") or "").strip()
        content = str(payload.get("content") or "")
        
        if not name:
            return JSONResponse({"ok": False, "error": "name is required"}, status_code=400)
        
        try:
            saved = state.memory.save(name=name, content=content)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        
        return {"ok": True, "file": saved, "files": state.memory.list_files()}
    
    @app.post("/api/telegram/restart")
    async def restart_telegram():
        restarted = state.telegram.restart()
        return {"ok": True, "restarted": restarted, "telegram": state.telegram.status()}
    
    @app.post("/api/telegram/test")
    async def test_telegram(payload: Dict[str, Any]):
        chat_id = str(payload.get("chat_id") or "").strip()
        message = str(payload.get("message") or "MiniClaw test message")
        
        if not chat_id:
            config = state.config_store.get()
            telegram_cfg = config.get("telegram", {})
            allowed_chat_ids = telegram_cfg.get("allowed_chat_ids", [])
            if allowed_chat_ids:
                chat_id = str(allowed_chat_ids[0]).strip()
        
        if not chat_id:
            return JSONResponse({"ok": False, "error": "chat_id is required or no bound chat available"}, status_code=400)
        
        state.telegram.send_test_message(chat_id=chat_id, message=message)
        return {"ok": True}
    
    @app.post("/api/telegram/unbind")
    async def unbind_telegram():
        result = state.telegram.unbind_chat(actor="api")
        return {"ok": True, "result": result, "telegram": state.telegram.status()}
    
    @app.post("/api/telegram/pairing/start")
    async def start_pairing(payload: Dict[str, Any]):
        ttl_seconds = payload.get("ttl_seconds")
        try:
            pairing = state.telegram.create_pairing_code(ttl_seconds=ttl_seconds)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        return {"ok": True, "pairing": pairing}
    
    @app.post("/api/telegram/pairing/confirm")
    async def confirm_pairing(payload: Dict[str, Any]):
        request_id = str(payload.get("request_id") or "").strip()
        if not request_id:
            return JSONResponse({"ok": False, "error": "request_id is required"}, status_code=400)
        
        try:
            resolved = state.telegram.resolve_pairing_request(request_id, approve=True, actor="api")
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        return {"ok": True, "request": resolved}
    
    @app.post("/api/telegram/pairing/claim")
    async def claim_pairing(payload: Dict[str, Any]):
        claim_code = str(payload.get("claim_code") or "").strip()
        if not claim_code:
            return JSONResponse({"ok": False, "error": "claim_code is required"}, status_code=400)
        
        try:
            resolved = state.telegram.resolve_pairing_code(claim_code, actor="api")
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        return {"ok": True, "request": resolved}
    
    @app.post("/api/telegram/pairing/reject")
    async def reject_pairing(payload: Dict[str, Any]):
        request_id = str(payload.get("request_id") or "").strip()
        if not request_id:
            return JSONResponse({"ok": False, "error": "request_id is required"}, status_code=400)
        
        try:
            resolved = state.telegram.resolve_pairing_request(request_id, approve=False, actor="api")
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        return {"ok": True, "request": resolved}
    
    @app.post("/api/skills/save")
    async def save_skill(payload: Dict[str, Any]):
        skill_id = str(payload.get("id") or "").strip()
        content = str(payload.get("content") or "")
        
        if not skill_id:
            return JSONResponse({"ok": False, "error": "id is required"}, status_code=400)
        if not content.strip():
            return JSONResponse({"ok": False, "error": "content is required"}, status_code=400)
        
        try:
            saved = state.skills.save_markdown_skill(skill_id, content)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        return {"ok": True, "skill": saved, "skills": state.skills.list()}
    
    @app.post("/api/skills/delete")
    async def delete_skill(payload: Dict[str, Any]):
        skill_id = str(payload.get("id") or "").strip()
        if not skill_id:
            return JSONResponse({"ok": False, "error": "id is required"}, status_code=400)
        
        try:
            deleted = state.skills.delete_skill(skill_id)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        return {"ok": True, "deleted": deleted, "skills": state.skills.list()}
    
    @app.post("/api/skills/settings")
    async def update_skill_settings(payload: Dict[str, Any]):
        enabled_skills = payload.get("enabled_skills") or []
        if not isinstance(enabled_skills, list):
            return JSONResponse({"ok": False, "error": "enabled_skills must be a list"}, status_code=400)
        
        min_score = int(payload.get("skill_match_min_score") or 2)
        settings = state.update_skill_settings(enabled_skills, min_score=min_score)
        return {"ok": True, "settings": settings}
    
    @app.post("/api/jobs/upsert")
    async def upsert_job(payload: Dict[str, Any]):
        try:
            job = state.upsert_job(payload)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        return {"ok": True, "job": job, "jobs": state.job_service.status()}
    
    @app.post("/api/jobs/delete")
    async def delete_job(payload: Dict[str, Any]):
        job_id = str(payload.get("id") or "").strip()
        if not job_id:
            return JSONResponse({"ok": False, "error": "id is required"}, status_code=400)
        
        try:
            deleted = state.delete_job(job_id)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        return {"ok": True, "deleted": deleted, "jobs": state.job_service.status()}
    
    @app.post("/api/jobs/run")
    async def run_job(payload: Dict[str, Any]):
        job_id = str(payload.get("id") or "").strip()
        if not job_id:
            return JSONResponse({"ok": False, "error": "id is required"}, status_code=400)
        
        try:
            result = state.job_service.trigger_now(job_id)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        return {"ok": True, "result": result, "jobs": state.job_service.status()}
    
    @app.post("/api/tools/run")
    async def run_tool(payload: Dict[str, Any]):
        tool_name = str(payload.get("tool") or "").strip()
        tool_args = payload.get("arguments") if isinstance(payload.get("arguments"), dict) else {}
        
        if not tool_name:
            return JSONResponse({"ok": False, "error": "tool is required"}, status_code=400)
        
        try:
            run_result = state.tools.run(tool_name, tool_args)
            return {"ok": True, "result": run_result}
        except Exception as exc:
            return JSONResponse({
                "ok": False,
                "error": str(exc),
                "result": {"ok": False, "tool": tool_name, "error": f"{exc.__class__.__name__}: {exc}"},
            })
    
    @app.post("/api/mcp/test")
    async def test_mcp(payload: Dict[str, Any]):
        server_id = str(payload.get("server_id") or "").strip()
        if not server_id:
            return JSONResponse({"ok": False, "error": "server_id is required"}, status_code=400)
        
        try:
            result = state.mcp.test_server(server_id)
            return {
                "ok": True,
                "success": result.get("ok", False),
                "message": f"Server responded in {result.get('duration_seconds', 0)}s",
                "error": None,
            }
        except Exception as exc:
            return {
                "ok": True,
                "success": False,
                "message": "",
                "error": str(exc),
            }
    
    @app.post("/api/plugins/reload")
    async def reload_plugins():
        state.plugins.reload()
        enabled = state.config_store.get()["agent"].get("enabled_plugins") or []
        state.plugins.set_enabled(enabled)
        return {"ok": True, "plugins": state.plugins.list()}
    
    @app.post("/v1/chat/completions")
    async def openai_proxy(request: Request):
        return await _handle_openai_proxy(request, state)
    
    @app.post("/v1/{path:path}")
    async def openai_proxy_catchall(path: str, request: Request):
        return await _handle_openai_proxy(request, state)
    
    return app


async def _handle_openai_proxy(request: Request, state: AppState):
    post_data = await request.body()
    content_type = request.headers.get("Content-Type", "application/json")
    
    try:
        if post_data:
            payload = json.loads(post_data.decode("utf-8"))
        else:
            payload = {}
    except json.JSONDecodeError:
        payload = {}
    
    model = payload.get("model", "")
    
    provider = None
    if model:
        for p in state.config_store.get().get("providers", {}).get("items", []):
            if p.get("model", "") == model and p.get("enabled", False):
                provider = p
                break
    
    if not provider:
        default_provider_id = state.config_store.get().get("providers", {}).get("default_provider_id")
        for p in state.config_store.get().get("providers", {}).get("items", []):
            if p.get("id") == default_provider_id and p.get("enabled", False):
                provider = p
                break
    
    if not provider:
        for p in state.config_store.get().get("providers", {}).get("items", []):
            if p.get("enabled", False):
                provider = p
                break
    
    if not provider:
        return JSONResponse({"ok": False, "error": "No enabled provider found"}, status_code=500)
    
    provider_type = provider.get("type", "ollama")
    base_url = provider.get("base_url", "").rstrip("/")
    api_key = provider.get("api_key", "")
    
    if request.url.path.startswith("/v1/"):
        target_path = request.url.path
    else:
        target_path = "/chat/completions"
    
    target_url = f"{base_url}{target_path}"
    
    headers = {
        "Content-Type": content_type,
        "Accept": "application/json",
    }
    
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    if provider_type == "openrouter":
        headers["HTTP-Referer"] = "https://miniclaw.ai"
        headers["X-Title"] = "MiniClaw"
    
    req = urllib.request.Request(
        url=target_url,
        data=post_data,
        headers=headers,
        method="POST"
    )
    
    ssl_context = None
    if target_url.startswith("https://") and not provider.get("verify_tls", True):
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        with urllib.request.urlopen(req, timeout=provider.get("timeout_seconds", 300), context=ssl_context) as response:
            response_data = response.read()
            return Response(
                content=response_data,
                status_code=response.status,
                headers=dict(response.headers),
                media_type=response.headers.get("Content-Type", "application/json"),
            )
    except urllib.error.HTTPError as e:
        return Response(
            content=e.read(),
            status_code=e.code,
            headers=dict(e.headers),
            media_type=e.headers.get("Content-Type", "application/json"),
        )
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Proxy error: {str(e)}"}, status_code=500)