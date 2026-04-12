"""Telegram bot: polling, pairing, progress updates."""
from __future__ import annotations

import copy
import json
import re
import secrets
from datetime import datetime, timezone
import threading
import time
import traceback
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from ..core.constants import PAIRING_ALPHABET
from ..core.config import ConfigStore
from ..core.events import EventLog
from ..core.agent import MiniClawAgent
from ..core.util import LOGGER, utc_now


class TelegramAPIError(RuntimeError):
    def __init__(self, method: str, status: int, detail: str) -> None:
        super().__init__(f"Telegram API error method={method} status={status}: {detail}")
        self.method = method
        self.status = status
        self.detail = detail


class TelegramConflictError(TelegramAPIError):
    pass


class TelegramService:
    def __init__(self, config_store: ConfigStore, event_log: EventLog, agent: MiniClawAgent) -> None:
        self._config_store = config_store
        self._event_log = event_log
        self._agent = agent
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event: Optional[threading.Event] = None
        self._offset = 0
        self._active_pairing: Optional[Dict[str, Any]] = None
        self._pairing_requests: Dict[str, Dict[str, Any]] = {}
        self._next_pairing_request_id = 1
        self._pending_tool_approvals: Dict[str, Dict[str, Any]] = {}
        self._next_tool_approval_id = 1

    def _telegram_api(
        self, token: str, method: str, payload: Dict[str, Any], timeout_seconds: int = 35
    ) -> Dict[str, Any]:
        url = f"https://api.telegram.org/bot{token}/{method}"
        redacted = f"https://api.telegram.org/bot***redacted***/{method}"
        data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            url=url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        self._event_log.add(
            "network.request",
            "Outgoing Telegram API request",
            {
                "method": method,
                "url": redacted,
                "payload": payload,
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8", errors="replace")
                parsed = json.loads(body) if body.strip() else {}
                self._event_log.add(
                    "network.response",
                    "Incoming Telegram API response",
                    {
                        "method": method,
                        "url": redacted,
                        "status": response.status,
                        "body": parsed,
                    },
                )
                if not isinstance(parsed, dict) or not parsed.get("ok", False):
                    detail = str(parsed)
                    raise TelegramAPIError(method, response.status, detail)
                return parsed
        except urllib.error.HTTPError as exc:
            # Try to read the response body, but handle cases where it's not available
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                # If we can't read the body, that's okay - we'll work with what we have
                pass
            parsed: Any
            try:
                parsed = json.loads(body) if body.strip() else {}
            except Exception:
                parsed = body
            detail = body
            if isinstance(parsed, dict):
                detail = str(parsed.get("description") or parsed)
            self._event_log.add(
                "network.error",
                "Telegram API request failed",
                {
                    "method": method,
                    "url": redacted,
                    "status": exc.code,
                    "body": parsed,
                    "detail": detail,
                },
            )
            if exc.code == 409:
                raise TelegramConflictError(method, exc.code, detail) from exc
            raise TelegramAPIError(method, exc.code, detail) from exc
        except urllib.error.URLError as exc:
            self._event_log.add(
                "network.error",
                "Telegram API request failed",
                {
                    "method": method,
                    "url": redacted,
                    "error": str(exc),
                },
            )
            raise TelegramAPIError(method, 0, str(exc)) from exc

    def _send_message(self, token: str, chat_id: Any, text: str) -> None:
        self._telegram_api(
            token,
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": text,
            },
        )

    def _send_typing(self, token: str, chat_id: Any) -> None:
        self._telegram_api(
            token,
            "sendChatAction",
            {
                "chat_id": chat_id,
                "action": "typing",
            },
            timeout_seconds=10,
        )

    def _telegram_token(self) -> str:
        config = self._config_store.get() or {}
        telegram_cfg = config.get("telegram") or {}
        token = str(telegram_cfg.get("bot_token") or "").strip()
        if not token:
            raise TelegramAPIError("sendMessage", 0, "Telegram bot token is missing")
        return token

    def _bound_chat_id(self, allowed_chat_ids: List[str]) -> str:
        normalized = [str(item).strip() for item in allowed_chat_ids if str(item).strip()]
        return normalized[0] if normalized else ""

    def _chat_allowed(self, chat_id: Any, allowed_chat_ids: List[str], pairing_required: bool) -> bool:
        bound_chat_id = self._bound_chat_id(allowed_chat_ids)
        if bound_chat_id and str(chat_id) == bound_chat_id:
            return True
        if bound_chat_id:
            return False
        return not pairing_required

    def _clean_pairing_locked(self) -> None:
        now = time.time()
        if self._active_pairing is not None and float(self._active_pairing.get("expires_at_epoch", 0)) < now:
            expired_code = self._active_pairing.get("code")
            self._active_pairing = None
            self._event_log.add(
                "telegram.pairing.expired",
                "Telegram pairing code expired",
                {"code": expired_code},
            )

    def _active_pairing_public_locked(self) -> Optional[Dict[str, Any]]:
        if self._active_pairing is None:
            return None
        return {
            "code": self._active_pairing.get("code"),
            "created_at": self._active_pairing.get("created_at"),
            "expires_at": self._active_pairing.get("expires_at"),
            "ttl_seconds": self._active_pairing.get("ttl_seconds"),
        }

    def _pairing_requests_public_locked(self) -> List[Dict[str, Any]]:
        requests = list(self._pairing_requests.values())
        requests.sort(key=lambda item: str(item.get("requested_at") or ""), reverse=True)
        return [copy.deepcopy(item) for item in requests]

    def _next_claim_code_locked(self) -> str:
        existing_codes = {
            str(item.get("claim_code") or "").upper()
            for item in self._pairing_requests.values()
            if str(item.get("claim_code") or "").strip()
        }
        if self._active_pairing is not None:
            existing_codes.add(str(self._active_pairing.get("code") or "").upper())
        while True:
            code = "".join(secrets.choice(PAIRING_ALPHABET) for _ in range(6))
            if code not in existing_codes:
                return code

    def _pending_pairing_for_chat_locked(self, chat_id_text: str) -> Optional[Dict[str, Any]]:
        for request in self._pairing_requests.values():
            if request.get("chat_id") == chat_id_text and request.get("status") == "pending":
                return request
        return None

    def _create_pairing_request_locked(
        self,
        chat_id_text: str,
        from_data: Dict[str, Any],
        source: str,
    ) -> Dict[str, Any]:
        existing_pending = self._pending_pairing_for_chat_locked(chat_id_text)
        if existing_pending is not None:
            return existing_pending
        request_id = f"pair-{self._next_pairing_request_id}"
        self._next_pairing_request_id += 1
        request_payload = {
            "request_id": request_id,
            "claim_code": self._next_claim_code_locked(),
            "chat_id": chat_id_text,
            "from": {
                "id": from_data.get("id"),
                "username": from_data.get("username"),
                "first_name": from_data.get("first_name"),
                "last_name": from_data.get("last_name"),
            },
            "status": "pending",
            "requested_at": utc_now(),
            "resolved_at": None,
            "resolved_by": None,
            "source": source,
        }
        self._pairing_requests[request_id] = request_payload
        return request_payload

    def _pairing_claim_message(self, request_payload: Dict[str, Any]) -> str:
        claim_code = str(request_payload.get("claim_code") or "").strip()
        request_id = str(request_payload.get("request_id") or "").strip()
        return (
            "This chat is not paired yet.\n"
            f"Claim code: {claim_code}\n"
            f"On the MiniClaw host run: miniclaw telegram pair-claim --code {claim_code}\n"
            f"Request id: {request_id}"
        )

    def status(self) -> Dict[str, Any]:
        with self._lock:
            self._clean_pairing_locked()
            running = self._thread is not None and self._thread.is_alive()
            pending = sum(1 for item in self._pairing_requests.values() if item.get("status") == "pending")
            config = self._config_store.get() or {}
            telegram_cfg = config.get("telegram") or {}
            bound_chat_id = self._bound_chat_id(telegram_cfg.get("allowed_chat_ids") or [])
            return {
                "running": running,
                "offset": self._offset,
                "active_pairing": self._active_pairing_public_locked(),
                "pending_pairing_requests": pending,
                "bound_chat_id": bound_chat_id,
            }

    def create_pairing_code(self, ttl_seconds: Optional[int] = None) -> Dict[str, Any]:
        telegram_cfg = (self._config_store.get() or {}).get("telegram") or {}
        ttl = int(ttl_seconds or telegram_cfg.get("pairing_code_ttl_seconds") or 600)
        ttl = max(60, ttl)
        code = "".join(secrets.choice(PAIRING_ALPHABET) for _ in range(6))
        now_epoch = time.time()
        payload = {
            "code": code,
            "created_at": utc_now(),
            "expires_at": datetime.fromtimestamp(now_epoch + ttl, tz=timezone.utc).isoformat(),
            "expires_at_epoch": now_epoch + ttl,
            "ttl_seconds": ttl,
        }
        with self._lock:
            self._active_pairing = payload

        self._event_log.add(
            "telegram.pairing.created",
            "Created Telegram pairing code",
            {
                "code": code,
                "ttl_seconds": ttl,
            },
        )
        LOGGER.info("Created Telegram pairing code ttl=%ds", ttl)
        return {
            "code": payload["code"],
            "created_at": payload["created_at"],
            "expires_at": payload["expires_at"],
            "ttl_seconds": payload["ttl_seconds"],
        }

    def pairing_status(self) -> Dict[str, Any]:
        with self._lock:
            self._clean_pairing_locked()
            config = self._config_store.get() or {}
            telegram_cfg = config.get("telegram") or {}
            return {
                "active_pairing": self._active_pairing_public_locked(),
                "requests": self._pairing_requests_public_locked(),
                "bound_chat_id": self._bound_chat_id(telegram_cfg.get("allowed_chat_ids") or []),
            }

    def resolve_pairing_code(self, claim_code: str, actor: str = "api") -> Dict[str, Any]:
        normalized_code = str(claim_code or "").strip().upper()
        if not normalized_code:
            raise ValueError("claim_code is required")
        with self._lock:
            self._clean_pairing_locked()
            target_request_id = ""
            for request_id, item in self._pairing_requests.items():
                if str(item.get("claim_code") or "").strip().upper() != normalized_code:
                    continue
                target_request_id = request_id
                break
        if not target_request_id:
            raise ValueError(f"Pairing claim code not found: {normalized_code}")
        return self.resolve_pairing_request(target_request_id, approve=True, actor=actor)

    def resolve_pairing_request(self, request_id: str, approve: bool, actor: str = "api") -> Dict[str, Any]:
        request_id = str(request_id or "").strip()
        if not request_id:
            raise ValueError("request_id is required")

        with self._lock:
            self._clean_pairing_locked()
            request = self._pairing_requests.get(request_id)
            if request is None:
                raise ValueError(f"Pairing request not found: {request_id}")
            if request.get("status") != "pending":
                return copy.deepcopy(request)
            chat_id = str(request.get("chat_id") or "")

        if approve:
            config = self._config_store.get() or {}
            telegram_cfg = config.get("telegram")
            if not isinstance(telegram_cfg, dict):
                config["telegram"] = {}
                telegram_cfg = config["telegram"]
            current_bound = self._bound_chat_id(telegram_cfg.get("allowed_chat_ids") or [])
            if current_bound and current_bound != chat_id:
                raise ValueError(
                    f"Telegram is already bound to chat {current_bound}. "
                    "Unbind it first before approving a different chat."
                )
            telegram_cfg["allowed_chat_ids"] = [chat_id] if chat_id else []
            self._config_store.save(config)
            self._event_log.add(
                "telegram.pairing.approved",
                "Approved Telegram pairing request",
                {
                    "request_id": request_id,
                    "chat_id": chat_id,
                    "actor": actor,
                },
            )
            LOGGER.info("Approved Telegram pairing request request_id=%s chat_id=%s", request_id, chat_id)
            try:
                self._send_message(
                    self._telegram_token(),
                    chat_id,
                    "Pairing complete. This chat is now connected to MiniClaw.",
                )
            except Exception:
                LOGGER.warning("Failed to send Telegram pairing approval notice chat_id=%s", chat_id, exc_info=True)
        else:
            self._event_log.add(
                "telegram.pairing.rejected",
                "Rejected Telegram pairing request",
                {
                    "request_id": request_id,
                    "chat_id": chat_id,
                    "actor": actor,
                },
            )
            LOGGER.info("Rejected Telegram pairing request request_id=%s chat_id=%s", request_id, chat_id)

        with self._lock:
            request = self._pairing_requests.get(request_id)
            if request is None:
                raise ValueError(f"Pairing request disappeared: {request_id}")
            request["status"] = "approved" if approve else "rejected"
            request["resolved_at"] = utc_now()
            request["resolved_by"] = actor
            return copy.deepcopy(request)

    def unbind_chat(self, actor: str = "api") -> Dict[str, Any]:
        config = self._config_store.get() or {}
        telegram_cfg = config.get("telegram")
        if not isinstance(telegram_cfg, dict):
            return {"removed_chat_id": "", "updated_allowed_chat_ids": []}
        bound_chat_id = self._bound_chat_id(telegram_cfg.get("allowed_chat_ids") or [])
        if not bound_chat_id:
            return {"removed_chat_id": "", "updated_allowed_chat_ids": []}

        telegram_cfg["allowed_chat_ids"] = []
        self._config_store.save(config)
        self._event_log.add(
            "telegram.unbound",
            "Removed Telegram chat binding",
            {
                "chat_id": bound_chat_id,
                "actor": actor,
            },
        )
        LOGGER.info("Removed Telegram chat binding chat_id=%s actor=%s", bound_chat_id, actor)
        return {"removed_chat_id": bound_chat_id, "updated_allowed_chat_ids": []}

    def _is_pair_command(self, text: str) -> bool:
        raw = str(text or "").strip()
        if not raw.startswith("/"):
            return False
        first = raw.split(maxsplit=1)[0].lower()
        return first == "/pair" or first.startswith("/pair@")

    def _is_new_session_command(self, text: str) -> bool:
        """Check if the text is a new session command (/new or /new@botname)."""
        raw = str(text or "").strip()
        if not raw.startswith("/"):
            return False
        first = raw.split(maxsplit=1)[0].lower()
        return first == "/new" or first.startswith("/new@")

    def _is_approval_command(self, text: str, command: str) -> bool:
        raw = str(text or "").strip()
        if not raw.startswith("/"):
            return False
        first = raw.split(maxsplit=1)[0].lower()
        return first == f"/{command}" or first.startswith(f"/{command}@")

    def _extract_command_argument(self, text: str) -> str:
        parts = str(text or "").strip().split(maxsplit=1)
        if len(parts) < 2:
            return ""
        return parts[1].strip()

    def _extract_pair_code(self, text: str) -> str:
        return self._extract_command_argument(text).upper()

    def _approval_public_payload_locked(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "request_id": item.get("request_id"),
            "chat_id": item.get("chat_id"),
            "tool_name": item.get("tool_name"),
            "reason": item.get("reason"),
            "status": item.get("status"),
            "requested_at": item.get("requested_at"),
            "resolved_at": item.get("resolved_at"),
            "resolved_by": item.get("resolved_by"),
        }

    def _latest_pending_approval_locked(self, chat_id_text: str) -> Optional[Dict[str, Any]]:
        pending = [
            item
            for item in self._pending_tool_approvals.values()
            if item.get("chat_id") == chat_id_text and item.get("status") == "pending"
        ]
        if not pending:
            return None
        pending.sort(key=lambda item: str(item.get("requested_at") or ""), reverse=True)
        return pending[0]

    def _resolve_tool_approval_locked(
        self,
        request_id: str,
        approve: bool,
        actor: str,
    ) -> Dict[str, Any]:
        item = self._pending_tool_approvals.get(request_id)
        if item is None:
            raise ValueError(f"Permission request not found: {request_id}")
        if item.get("status") != "pending":
            return self._approval_public_payload_locked(item)
        item["status"] = "approved" if approve else "denied"
        item["approved"] = approve
        item["resolved_at"] = utc_now()
        item["resolved_by"] = actor
        event = item.get("_event")
        if isinstance(event, threading.Event):
            event.set()
        return self._approval_public_payload_locked(item)

    def request_tool_permission(
        self,
        chat_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 300,
    ) -> bool:
        chat_id_text = str(chat_id or "").strip()
        if not chat_id_text:
            return False
        token = self._telegram_token()
        wait_timeout = max(5, int(timeout_seconds or 300))
        approval_event = threading.Event()

        with self._lock:
            request_id = f"perm-{self._next_tool_approval_id}"
            self._next_tool_approval_id += 1
            payload = {
                "request_id": request_id,
                "chat_id": chat_id_text,
                "tool_name": str(tool_name or "").strip(),
                "arguments": copy.deepcopy(arguments) if isinstance(arguments, dict) else {},
                "reason": str(reason or "").strip() or f"Run tool {tool_name}",
                "details": details or {},
                "status": "pending",
                "requested_at": utc_now(),
                "resolved_at": None,
                "resolved_by": None,
                "approved": None,
                "_event": approval_event,
            }
            self._pending_tool_approvals[request_id] = payload

        # Build Telegram-friendly message with full command details
        message_lines = ["⚠️ Permission needed to run tool\n"]
        message_lines.append(f"Tool: {tool_name}")
        
        if details:
            if tool_name == "run_command":
                cmd = details.get("command", "")
                cwd = details.get("cwd", ".")
                message_lines.append(f"\n📁 Working directory: `{cwd}`")
                message_lines.append(f"\n🔧 Command:\n```\n{cmd}\n```")
            elif tool_name == "write_file":
                path = details.get("path", "")
                preview = details.get("content_preview", "")
                length = details.get("content_length", 0)
                message_lines.append(f"\n📄 File: `{path}`")
                message_lines.append(f"\n📝 Content preview:\n```\n{preview}\n```")
                message_lines.append(f"\nSize: {length} characters")
            elif tool_name == "mcp_call_tool":
                server = details.get("server", "")
                tool = details.get("tool", "")
                args = details.get("arguments", {})
                message_lines.append(f"\n🖥️ Server: `{server}`")
                message_lines.append(f"\n🔧 Tool: `{tool}`")
                message_lines.append(f"\n📋 Arguments: `{json.dumps(args)}`")
            else:
                message_lines.append(f"\nDetails: {json.dumps(details)}")
        
        message_lines.append(f"\n{reason}")
        message_lines.append(f"\nID: `{request_id}`")
        message_lines.append(f"\nReply with `/approve {request_id}` or `/deny {request_id}`")
        
        message = "\n".join(message_lines)
        self._send_message(token, chat_id_text, message)
        self._event_log.add(
            "telegram.permission.requested",
            "Requested Telegram approval for tool execution",
            {
                "chat_id": chat_id_text,
                "request_id": request_id,
                "tool_name": tool_name,
                "reason": payload["reason"],
            },
        )

        approved = approval_event.wait(timeout=wait_timeout)
        with self._lock:
            item = self._pending_tool_approvals.get(request_id)
            if item is None:
                return False
            if not approved and item.get("status") == "pending":
                item["status"] = "expired"
                item["approved"] = False
                item["resolved_at"] = utc_now()
                item["resolved_by"] = "timeout"
            final_status = str(item.get("status") or "denied")
            final_decision = bool(item.get("approved") is True)
            self._pending_tool_approvals.pop(request_id, None)

        if final_status == "expired":
            self._send_message(
                token,
                chat_id_text,
                f"Permission request {request_id} timed out, so I stopped before running {tool_name}.",
            )
            self._event_log.add(
                "telegram.permission.expired",
                "Telegram permission request timed out",
                {
                    "chat_id": chat_id_text,
                    "request_id": request_id,
                    "tool_name": tool_name,
                },
            )
        return final_decision

    def _handle_tool_approval_command(
        self,
        token: str,
        chat_id: Any,
        from_data: Dict[str, Any],
        text: str,
    ) -> bool:
        approve = self._is_approval_command(text, "approve")
        deny = self._is_approval_command(text, "deny")
        if not approve and not deny:
            return False

        chat_id_text = str(chat_id)
        request_id = self._extract_command_argument(text)
        actor = (
            str(from_data.get("username") or "").strip()
            or str(from_data.get("id") or "").strip()
            or "telegram"
        )

        with self._lock:
            target: Optional[Dict[str, Any]]
            if request_id:
                target = self._pending_tool_approvals.get(request_id)
            else:
                target = self._latest_pending_approval_locked(chat_id_text)
            if target is None:
                self._send_message(
                    token,
                    chat_id,
                    "No pending permission request was found. Reply with /approve <ID> or /deny <ID> when prompted.",
                )
                return True
            if str(target.get("chat_id") or "") != chat_id_text:
                self._send_message(
                    token,
                    chat_id,
                    "That permission request belongs to a different chat and cannot be controlled here.",
                )
                return True
            resolved = self._resolve_tool_approval_locked(
                str(target.get("request_id") or request_id),
                approve=approve,
                actor=actor,
            )

        decision_text = "approved" if approve else "denied"
        self._send_message(
            token,
            chat_id,
            f"{decision_text.capitalize()} {resolved.get('request_id')} for {resolved.get('tool_name')}.",
        )
        self._event_log.add(
            "telegram.permission.resolved",
            "Resolved Telegram permission request",
            {
                "chat_id": chat_id_text,
                "request_id": resolved.get("request_id"),
                "tool_name": resolved.get("tool_name"),
                "decision": decision_text,
                "actor": actor,
            },
        )
        return True

    def _handle_pair_command(self, token: str, chat_id: Any, from_data: Dict[str, Any], text: str) -> bool:
        if not self._is_pair_command(text):
            return False

        chat_id_text = str(chat_id)
        code = self._extract_pair_code(text)
        reply_text = ""
        event_type = ""
        event_message = ""
        event_details: Dict[str, Any] = {}
        request_payload: Optional[Dict[str, Any]] = None

        with self._lock:
            self._clean_pairing_locked()
            active = self._active_pairing
            if not code:
                reply_text = "Pairing usage: /pair <CODE>. Create a code in the MiniClaw Setup page first."
                event_type = "telegram.pairing.usage"
                event_message = "Telegram pairing command missing code"
                event_details = {"chat_id": chat_id_text}
            elif active is None:
                reply_text = (
                    "No active pairing code. Send any normal message instead and MiniClaw will reply "
                    "with a one-time claim code for the CLI."
                )
                event_type = "telegram.pairing.invalid"
                event_message = "Pairing attempt rejected because no code is active"
                event_details = {"chat_id": chat_id_text, "submitted_code": code}
            else:
                expected_code = str(active.get("code") or "").upper()
                if code != expected_code:
                    reply_text = "Invalid pairing code."
                    event_type = "telegram.pairing.invalid"
                    event_message = "Pairing attempt used wrong code"
                    event_details = {"chat_id": chat_id_text, "submitted_code": code}
                else:
                    telegram_cfg = (self._config_store.get() or {}).get("telegram") or {}
                    allowed_chat_ids = [
                        str(item) for item in telegram_cfg.get("allowed_chat_ids") or []
                    ]
                    current_bound = self._bound_chat_id(allowed_chat_ids)
                    if current_bound and current_bound == chat_id_text:
                        reply_text = "This chat is already paired."
                        event_type = "telegram.pairing.skip"
                        event_message = "Pairing attempt skipped because chat is already paired"
                        event_details = {"chat_id": chat_id_text}
                    elif current_bound and current_bound != chat_id_text:
                        reply_text = (
                            f"MiniClaw is already paired to chat {current_bound}. "
                            "Admin must unbind it before pairing a new chat."
                        )
                        event_type = "telegram.pairing.blocked"
                        event_message = "Pairing attempt blocked by single-chat binding rule"
                        event_details = {
                            "chat_id": chat_id_text,
                            "bound_chat_id": current_bound,
                        }
                    else:
                        existing_pending = self._pending_pairing_for_chat_locked(chat_id_text)
                        if existing_pending is not None:
                            reply_text = self._pairing_claim_message(existing_pending)
                            event_type = "telegram.pairing.pending"
                            event_message = "Pairing request already pending"
                            event_details = {
                                "chat_id": chat_id_text,
                                "request_id": existing_pending.get("request_id"),
                                "claim_code": existing_pending.get("claim_code"),
                            }
                        else:
                            request_payload = self._create_pairing_request_locked(
                                chat_id_text,
                                from_data,
                                source="pair_command",
                            )
                            reply_text = self._pairing_claim_message(request_payload)
                            event_type = "telegram.pairing.requested"
                            event_message = "Received Telegram pairing request"
                            event_details = {
                                "chat_id": chat_id_text,
                                "request_id": request_payload.get("request_id"),
                                "from": request_payload["from"],
                                "claim_code": request_payload.get("claim_code"),
                            }

        self._send_message(token, chat_id, reply_text)
        self._event_log.add(event_type, event_message, event_details)
        if request_payload is not None:
            LOGGER.info(
                "Pairing request created request_id=%s chat_id=%s",
                request_payload["request_id"],
                chat_id_text,
            )
        return True

    def _issue_cli_claim_code(self, token: str, chat_id: Any, from_data: Dict[str, Any]) -> None:
        chat_id_text = str(chat_id)
        with self._lock:
            request_payload = self._create_pairing_request_locked(
                chat_id_text,
                from_data,
                source="auto_claim",
            )
        self._send_message(token, chat_id, self._pairing_claim_message(request_payload))
        self._event_log.add(
            "telegram.pairing.claim_issued",
            "Issued CLI claim code for Telegram pairing",
            {
                "chat_id": chat_id_text,
                "request_id": request_payload.get("request_id"),
                "claim_code": request_payload.get("claim_code"),
            },
        )

    def _handle_new_session_command(self, token: str, chat_id: Any, text: str) -> bool:
        """Handle the /new command to start a new conversation session."""
        if not self._is_new_session_command(text):
            return False

        try:
            # Create a new session instead of just clearing history
            new_session_id = self._agent.create_session(meta={"chat_id": chat_id})
            
            # Send confirmation message
            reply_text = "Starting a new conversation session. How can I help you?"
            self._send_message(token, chat_id, reply_text)
            
            # Log the event
            self._event_log.add(
                "telegram.new_session",
                "Started new conversation session",
                {"chat_id": str(chat_id), "session_id": new_session_id},
            )
            
            return True
        except Exception as e:
            LOGGER.error("Error handling /new command: %s", str(e), exc_info=True)
            self._send_message(token, chat_id, "Sorry, I couldn't start a new session. Please try again.")
            return True

    def _ensure_polling_mode(self, token: str) -> None:
        try:
            self._telegram_api(
                token,
                "deleteWebhook",
                {
                    "drop_pending_updates": False,
                },
            )
            self._event_log.add(
                "telegram.webhook.cleared",
                "Ensured Telegram webhook is disabled for polling",
                {},
            )
            LOGGER.info("Ensured Telegram webhook is disabled for polling")
        except TelegramAPIError as exc:
            self._event_log.add(
                "telegram.webhook.error",
                "Failed to disable Telegram webhook before polling",
                {
                    "error": str(exc),
                },
            )
            LOGGER.warning("Failed to disable webhook before polling: %s", exc)

    def start_if_enabled(self) -> None:
        config = self._config_store.get() or {}
        telegram_cfg = config.get("telegram") or {}

        if not telegram_cfg.get("enabled"):
            self._event_log.add("telegram.disabled", "Telegram integration disabled", {})
            return

        token = str(telegram_cfg.get("bot_token") or "").strip()
        if not token:
            self._event_log.add("telegram.error", "Telegram enabled but bot token is missing", {})
            return

        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                LOGGER.info("Telegram poller already running; start skipped")
                return
        self._ensure_polling_mode(token)
        with self._lock:
            self._stop_event = threading.Event()
            self._thread = threading.Thread(target=self._run, args=(token,), daemon=True, name="miniclaw-telegram")
            self._thread.start()

        self._event_log.add("telegram.started", "Started Telegram poller", {})
        LOGGER.info("Started Telegram poller")

    def stop(self, wait_timeout_seconds: int = 20) -> bool:
        with self._lock:
            thread = self._thread
            stop_event = self._stop_event
        if thread is None:
            return True

        if stop_event is not None:
            stop_event.set()
        thread.join(timeout=max(1, int(wait_timeout_seconds)))

        if thread.is_alive():
            self._event_log.add(
                "telegram.stop.pending",
                "Telegram poller did not stop before timeout",
                {"timeout_seconds": int(wait_timeout_seconds)},
            )
            LOGGER.warning(
                "Telegram poller still running after %ss; skipping restart to avoid duplicate pollers",
                wait_timeout_seconds,
            )
            return False

        with self._lock:
            if self._thread is thread:
                self._thread = None
            if self._stop_event is stop_event:
                self._stop_event = None

        self._event_log.add("telegram.stopped", "Stopped Telegram poller", {})
        LOGGER.info("Stopped Telegram poller")
        return True

    def restart(self) -> bool:
        stopped = self.stop()
        if not stopped:
            self._event_log.add(
                "telegram.restart.skipped",
                "Skipped Telegram restart because previous poller has not fully stopped",
                {},
            )
            return False
        self.start_if_enabled()
        return True

    def send_test_message(self, chat_id: str, message: str) -> None:
        config = self._config_store.get() or {}
        telegram_cfg = config.get("telegram") or {}
        token = str(telegram_cfg.get("bot_token") or "").strip()
        if not token:
            raise RuntimeError("Telegram token is empty")

        self._telegram_api(
            token,
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": message,
            },
        )
        self._event_log.add(
            "telegram.test",
            "Sent Telegram test message",
            {
                "chat_id": str(chat_id),
                "message": message,
            },
        )

    def _split_telegram_message(self, text: str, max_chars: int = 3500) -> List[str]:
        raw = str(text or "").strip()
        if not raw:
            return []
        chunks: List[str] = []
        remaining = raw
        while len(remaining) > max_chars:
            split_at = remaining.rfind("\n", 0, max_chars)
            if split_at <= 0:
                split_at = max_chars
            chunks.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].strip()
        if remaining:
            chunks.append(remaining)
        return chunks

    def _wants_multi_part_delivery(self, user_text: str) -> bool:
        lowered = str(user_text or "").lower()
        markers = [
            "one message at a time",
            "message at a time",
            "one at a time",
            "in parts",
            "step by step",
            "message by message",
        ]
        return any(marker in lowered for marker in markers)

    def _split_for_multi_part_delivery(self, text: str, max_parts: int = 12) -> List[str]:
        stripped = str(text or "").strip()
        if not stripped:
            return []

        lines = [line.strip() for line in stripped.splitlines() if line.strip()]
        if len(lines) >= 2:
            return lines[:max_parts]

        numbered = re.findall(r"(?:^|\n)\s*(\d+[.)]?\s+[^\n]+)", stripped)
        if len(numbered) >= 2:
            return [item.strip() for item in numbered[:max_parts]]

        sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", stripped) if item.strip()]
        if len(sentences) >= 2:
            return sentences[:max_parts]

        return self._split_telegram_message(stripped, max_chars=900)[:max_parts]

    def _parse_count_sequence_request(self, text: str) -> Optional[Dict[str, int]]:
        lowered = str(text or "").lower()
        if "count" not in lowered:
            return None
        if not self._wants_multi_part_delivery(lowered):
            return None
        match = re.search(r"count(?:\s+from)?\s+(-?\d+)\s*(?:to|-|through)\s*(-?\d+)", lowered)
        if not match:
            return None
        start = int(match.group(1))
        end = int(match.group(2))
        size = abs(end - start) + 1
        if size > 200:
            raise ValueError("Count range is too large. Max supported range size is 200.")
        return {"start": start, "end": end, "size": size}

    def _process_authorized_message(
        self,
        token: str,
        chat_id: Any,
        from_data: Dict[str, Any],
        text: str,
    ) -> None:
        self._event_log.add(
            "telegram.message.received",
            "Received Telegram message",
            {
                "chat_id": str(chat_id),
                "text": text,
            },
        )

        config = (self._config_store.get() or {}).get("telegram") or {}
        progress_interval = max(5, int(config.get("progress_update_seconds") or 12))
        processing_started_at = time.time()
        progress_state = {
            "stage": "working",
            "last_sent_at": 0.0,
            "initial_ack_sent": False,
            "update_count": 0,
            "tool_history": [],
        }
        progress_done = threading.Event()
        typing_done = threading.Event()

        def send_progress(text_message: str, force: bool = False) -> None:
            now = time.time()
            if not progress_state["initial_ack_sent"] and now - processing_started_at >= 5:
                try:
                    self._send_message(token, chat_id, "Working on it.")
                    progress_state["initial_ack_sent"] = True
                except Exception as exc:
                    self._event_log.add(
                        "telegram.progress.error",
                        "Failed to send Telegram progress acknowledgement",
                        {
                            "chat_id": str(chat_id),
                            "error": f"{exc.__class__.__name__}: {exc}",
                        },
                    )

            if progress_state["initial_ack_sent"]:
                if not force and now - float(progress_state["last_sent_at"]) < progress_interval:
                    return
                progress_state["last_sent_at"] = now
                elapsed = int(now - processing_started_at)
                if elapsed < 10:
                    return
                update_count = int(progress_state.get("update_count") or 0)
                if update_count >= 3:
                    return

                descriptive_updates = {
                    "analyze": "Inspecting your request and figuring out the coding plan.",
                    "plugins": "Loading relevant project context and working notes.",
                    "model_call": "Planning the next step.",
                    "tool_call": "Using project tools to inspect files, edit code, or run commands.",
                    "finalize": "Wrapping up the work and summarizing results.",
                    "final": "Finishing the response.",
                }

                human_message = text_message
                if text_message.startswith("model "):
                    human_message = "Thinking through the next coding step."
                elif text_message.startswith("tool "):
                    tool_name = text_message[5:]
                    if tool_name not in progress_state["tool_history"]:
                        progress_state["tool_history"].append(tool_name)
                    if tool_name == "run_command":
                        human_message = "Running a project command."
                    elif tool_name == "list_dir":
                        human_message = "Inspecting the repo layout."
                    elif tool_name == "read_file":
                        human_message = "Reading project files."
                    elif tool_name == "write_file":
                        human_message = "Applying a file update."
                    elif tool_name == "fetch_url":
                        human_message = "Fetching documentation from the web."
                    elif tool_name == "browser_extract":
                        human_message = "Reading a webpage for context."
                    else:
                        human_message = f"Using {tool_name} to keep moving."
                    if len(progress_state["tool_history"]) > 1 and update_count >= 2:
                        human_message = (
                            f"Still working. I have used {len(progress_state['tool_history'])} different tools so far."
                        )
                else:
                    human_message = descriptive_updates.get(text_message, "Still working on your request.")

                try:
                    self._send_message(token, chat_id, human_message)
                    progress_state["update_count"] = update_count + 1
                except Exception as exc:
                    self._event_log.add(
                        "telegram.progress.error",
                        "Failed to send Telegram progress update",
                        {
                            "chat_id": str(chat_id),
                            "error": f"{exc.__class__.__name__}: {exc}",
                        },
                    )

        def on_status(stage_message: str) -> None:
            compact = str(stage_message or "").strip() or "working"
            progress_state["stage"] = compact
            send_progress(compact)

        def progress_heartbeat() -> None:
            while not progress_done.wait(timeout=progress_interval):
                stage = str(progress_state.get("stage") or "working")
                send_progress(stage, force=True)

        def typing_heartbeat() -> None:
            while not typing_done.wait(timeout=4):
                try:
                    self._send_typing(token, chat_id)
                except Exception as exc:
                    self._event_log.add(
                        "telegram.typing.error",
                        "Failed to send typing action",
                        {
                            "chat_id": str(chat_id),
                            "error": f"{exc.__class__.__name__}: {exc}",
                        },
                    )

        try:
            self._send_typing(token, chat_id)
        except Exception:
            pass
        progress_thread = threading.Thread(
            target=progress_heartbeat,
            daemon=True,
            name="miniclaw-telegram-progress",
        )
        typing_thread = threading.Thread(
            target=typing_heartbeat,
            daemon=True,
            name="miniclaw-telegram-typing",
        )
        progress_thread.start()
        typing_thread.start()

        try:
            result = self._agent.chat_with_updates(
                text,
                source="telegram",
                meta={
                    "chat_id": str(chat_id),
                    "from": from_data,
                },
                status_callback=on_status,
            )
            answer = str(result.get("response") or "")
        except Exception as exc:
            answer = f"MiniClaw error: {exc}"
        finally:
            progress_done.set()
            typing_done.set()
            progress_thread.join(timeout=1)
            typing_thread.join(timeout=1)

        multi_part_requested = self._wants_multi_part_delivery(text)
        if multi_part_requested:
            chunks = self._split_for_multi_part_delivery(answer)
        else:
            chunks = self._split_telegram_message(answer)
        if not chunks:
            chunks = ["(empty response)"]
        for index, chunk in enumerate(chunks):
            try:
                self._send_typing(token, chat_id)
            except Exception:
                pass
            self._send_message(token, chat_id, chunk)
            if multi_part_requested and index < len(chunks) - 1:
                time.sleep(0.6)

        self._event_log.add(
            "telegram.message.sent",
            "Sent Telegram response",
            {
                "chat_id": str(chat_id),
                "text": answer,
            },
        )

    def _run(self, token: str) -> None:
        self._event_log.add("telegram.loop", "Telegram polling loop started", {})
        LOGGER.info("Telegram polling loop started")
        conflict_streak = 0
        last_conflict_log_at = 0.0
        while True:
            with self._lock:
                stop_event = self._stop_event

            if stop_event is None or stop_event.is_set():
                break

            config = (self._config_store.get() or {}).get("telegram") or {}
            poll_interval = max(1, int(config.get("poll_interval_seconds") or 2))
            pairing_required = bool(config.get("pairing_required", True))

            try:
                updates = self._telegram_api(
                    token,
                    "getUpdates",
                    {
                        "offset": self._offset,
                        "timeout": 10,
                        "allowed_updates": ["message"],
                    },
                    timeout_seconds=15,
                )
                conflict_streak = 0
                for update in updates.get("result", []):
                    if not isinstance(update, dict):
                        continue
                    update_id = int(update.get("update_id") or 0)
                    if update_id >= self._offset:
                        self._offset = update_id + 1

                    message = update.get("message")
                    if not isinstance(message, dict):
                        continue
                    text = str(message.get("text") or "").strip()
                    chat = message.get("chat") or {}
                    chat_id = chat.get("id")
                    from_data = message.get("from") or {}
                    if not text:
                        self._event_log.add(
                            "telegram.skip",
                            "Ignored Telegram update without text",
                            {"chat_id": chat_id},
                        )
                        continue
                    if self._handle_pair_command(token, chat_id, from_data, text):
                        continue

                    if self._handle_new_session_command(token, chat_id, text):
                        continue

                    if self._handle_tool_approval_command(token, chat_id, from_data, text):
                        continue

                    if not self._chat_allowed(chat_id, config.get("allowed_chat_ids") or [], pairing_required):
                        bound_chat_id = self._bound_chat_id(config.get("allowed_chat_ids") or [])
                        self._event_log.add(
                            "telegram.denied",
                            "Ignored Telegram message from unauthorized chat",
                            {"chat_id": str(chat_id), "bound_chat_id": bound_chat_id},
                        )
                        if bound_chat_id:
                            denial = (
                                f"MiniClaw is bound to chat {bound_chat_id}. "
                                "Admin must unbind it before pairing a different chat."
                            )
                            self._send_message(
                                token,
                                chat_id,
                                denial,
                            )
                        else:
                            self._issue_cli_claim_code(token, chat_id, from_data)
                        continue

                    try:
                        count_request = self._parse_count_sequence_request(text)
                    except ValueError as exc:
                        self._send_message(token, chat_id, f"MiniClaw error: {exc}")
                        continue
                    if count_request is not None:
                        start = count_request["start"]
                        end = count_request["end"]
                        step = 1 if end >= start else -1
                        total = count_request["size"]
                        self._event_log.add(
                            "telegram.count.start",
                            "Running built-in count sequence task",
                            {"chat_id": str(chat_id), "start": start, "end": end, "total": total},
                        )
                        self._send_message(
                            token,
                            chat_id,
                            f"MiniClaw update 0s: counting {start} to {end}",
                        )
                        sent = 0
                        for number in range(start, end + step, step):
                            try:
                                self._send_typing(token, chat_id)
                            except Exception:
                                pass
                            self._send_message(token, chat_id, str(number))
                            sent += 1
                            if sent < total:
                                time.sleep(0.6)
                        self._event_log.add(
                            "telegram.count.done",
                            "Completed built-in count sequence task",
                            {"chat_id": str(chat_id), "count": sent},
                        )
                        continue
                    worker = threading.Thread(
                        target=self._process_authorized_message,
                        args=(token, chat_id, from_data, text),
                        daemon=True,
                        name="miniclaw-telegram-message",
                    )
                    worker.start()
            except TelegramConflictError as exc:
                conflict_streak += 1
                backoff_seconds = min(30, max(poll_interval, 2 * min(conflict_streak, 10)))
                now = time.time()
                # 409 is expected when another getUpdates session (or webhook mode) is active.
                if now - last_conflict_log_at >= 20:
                    self._event_log.add(
                        "telegram.conflict",
                        "Telegram long-polling conflict",
                        {
                            "error": str(exc),
                            "streak": conflict_streak,
                            "backoff_seconds": backoff_seconds,
                        },
                    )
                    LOGGER.warning(
                        "Telegram getUpdates conflict (HTTP 409). Another poller or webhook may be active. "
                        "backoff=%ss streak=%s",
                        backoff_seconds,
                        conflict_streak,
                    )
                    last_conflict_log_at = now
                time.sleep(backoff_seconds)
                continue
            except TelegramAPIError as exc:
                self._event_log.add(
                    "telegram.error",
                    "Telegram polling API error",
                    {
                        "error": str(exc),
                    },
                )
                LOGGER.warning("Telegram polling API error: %s", exc)
            except Exception as exc:
                self._event_log.add(
                    "telegram.error",
                    "Telegram polling failed",
                    {
                        "error": f"{exc.__class__.__name__}: {exc}",
                        "traceback": traceback.format_exc(limit=10),
                    },
                )
                LOGGER.exception("Telegram polling error")

            time.sleep(poll_interval)

        self._event_log.add("telegram.loop", "Telegram polling loop ended", {})
        LOGGER.info("Telegram polling loop ended")
