"""WhatsApp integration using wacli."""
from __future__ import annotations

import json
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional

from ..core.config import ConfigStore
from ..core.events import EventLog
from ..core.agent import MiniClawAgent
from ..core.util import LOGGER


class WhatsAppError(RuntimeError):
    pass


class WhatsAppService:
    def __init__(self, config_store: ConfigStore, event_log: EventLog, agent: MiniClawAgent) -> None:
        self._config_store = config_store
        self._event_log = event_log
        self._agent = agent
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event: Optional[threading.Event] = None
        self._last_message_time = 0.0

    def _wacli_api(self, command: str, args: List[str], timeout_seconds: int = 30) -> Dict[str, Any]:
        """Execute wacli command and return parsed JSON response."""
        config = self._config_store.get() or {}
        whatsapp_cfg = config.get("channels", {}).get("whatsapp_wacli", {}) or {}
        wacli_cmd = str(whatsapp_cfg.get("wacli_command") or "wacli").strip()

        cmd = [wacli_cmd, command] + args

        self._event_log.add(
            "whatsapp.command",
            "Executing wacli command",
            {
                "command": command,
                "args": args,
                "full_command": " ".join(cmd),
            },
        )

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=True
            )

            # Try to parse JSON output, fallback to text if not valid JSON
            try:
                output = json.loads(result.stdout) if result.stdout.strip() else {}
            except json.JSONDecodeError:
                output = {"text": result.stdout.strip()}

            self._event_log.add(
                "whatsapp.response",
                "wacli command response",
                {
                    "command": command,
                    "returncode": result.returncode,
                    "stdout": result.stdout[:1000],  # Limit log size
                    "stderr": result.stderr[:1000],  # Limit log size
                },
            )

            return output
        except subprocess.TimeoutExpired as exc:
            self._event_log.add(
                "whatsapp.timeout",
                "wacli command timed out",
                {
                    "command": command,
                    "timeout_seconds": timeout_seconds,
                    "error": str(exc),
                },
            )
            raise WhatsAppError(f"wacli command timed out: {command}") from exc
        except subprocess.CalledProcessError as exc:
            self._event_log.add(
                "whatsapp.error",
                "wacli command failed",
                {
                    "command": command,
                    "returncode": exc.returncode,
                    "stdout": exc.stdout[:1000] if exc.stdout else "",
                    "stderr": exc.stderr[:1000] if exc.stderr else "",
                    "error": str(exc),
                },
            )
            raise WhatsAppError(f"wacli command failed: {command} - {exc.stderr}") from exc
        except Exception as exc:
            self._event_log.add(
                "whatsapp.error",
                "wacli command error",
                {
                    "command": command,
                    "error": str(exc),
                },
            )
            raise WhatsAppError(f"wacli command error: {command} - {exc}") from exc

    def _send_message(self, contact: str, text: str) -> None:
        """Send a message to a WhatsApp contact."""
        self._wacli_api("send", [contact, text])

    def status(self) -> Dict[str, Any]:
        """Get WhatsApp service status."""
        with self._lock:
            running = self._thread is not None and self._thread.is_alive()
            config = self._config_store.get() or {}
            whatsapp_cfg = config.get("channels", {}).get("whatsapp_wacli", {}) or {}
            return {
                "running": running,
                "enabled": bool(whatsapp_cfg.get("enabled", False)),
                "wacli_command": whatsapp_cfg.get("wacli_command", "wacli"),
                "last_message_time": self._last_message_time,
            }

    def send_test_message(self, contact: str, message: str) -> None:
        """Send a test message to a WhatsApp contact."""
        config = self._config_store.get() or {}
        whatsapp_cfg = config.get("channels", {}).get("whatsapp_wacli", {}) or {}

        if not whatsapp_cfg.get("enabled", False):
            raise WhatsAppError("WhatsApp integration is not enabled")

        if not contact.strip():
            raise WhatsAppError("Contact is required")

        self._send_message(contact, message)
        self._event_log.add(
            "whatsapp.test",
            "Sent WhatsApp test message",
            {
                "contact": contact,
                "message": message,
            },
        )

    def start_if_enabled(self) -> None:
        """Start WhatsApp polling if enabled."""
        config = self._config_store.get() or {}
        whatsapp_cfg = config.get("channels", {}).get("whatsapp_wacli", {}) or {}

        if not whatsapp_cfg.get("enabled", False):
            self._event_log.add("whatsapp.disabled", "WhatsApp integration disabled", {})
            return

        wacli_cmd = str(whatsapp_cfg.get("wacli_command") or "wacli").strip()
        if not wacli_cmd:
            self._event_log.add("whatsapp.error", "WhatsApp enabled but wacli command is missing", {})
            return

        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                LOGGER.info("WhatsApp poller already running; start skipped")
                return

        with self._lock:
            self._stop_event = threading.Event()
            self._thread = threading.Thread(target=self._run, daemon=True, name="miniclaw-whatsapp")
            self._thread.start()

        self._event_log.add("whatsapp.started", "Started WhatsApp poller", {})
        LOGGER.info("Started WhatsApp poller")

    def stop(self, wait_timeout_seconds: int = 20) -> bool:
        """Stop WhatsApp polling."""
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
                "whatsapp.stop.pending",
                "WhatsApp poller did not stop before timeout",
                {"timeout_seconds": int(wait_timeout_seconds)},
            )
            LOGGER.warning(
                "WhatsApp poller still running after %ss; skipping restart",
                wait_timeout_seconds,
            )
            return False

        with self._lock:
            if self._thread is thread:
                self._thread = None
            if self._stop_event is stop_event:
                self._stop_event = None

        self._event_log.add("whatsapp.stopped", "Stopped WhatsApp poller", {})
        LOGGER.info("Stopped WhatsApp poller")
        return True

    def restart(self) -> bool:
        """Restart WhatsApp polling."""
        stopped = self.stop()
        if not stopped:
            self._event_log.add(
                "whatsapp.restart.skipped",
                "Skipped WhatsApp restart because previous poller has not fully stopped",
                {},
            )
            return False
        self.start_if_enabled()
        return True

    def _run(self) -> None:
        """Main polling loop for WhatsApp messages."""
        self._event_log.add("whatsapp.loop", "WhatsApp polling loop started", {})
        LOGGER.info("WhatsApp polling loop started")

        while True:
            with self._lock:
                stop_event = self._stop_event

            if stop_event is None or stop_event.is_set():
                break

            config = (self._config_store.get() or {}).get("channels", {}).get("whatsapp_wacli", {}) or {}
            poll_interval = max(5, int(config.get("poll_interval_seconds") or 15))
            allowed_contacts = config.get("allowed_contacts") or []

            try:
                # Check for new messages
                messages = self._wacli_api("receive", ["--json"])

                if isinstance(messages, dict) and "messages" in messages:
                    for msg in messages["messages"]:
                        self._process_message(msg, allowed_contacts)

            except WhatsAppError as exc:
                self._event_log.add(
                    "whatsapp.poll.error",
                    "WhatsApp polling error",
                    {
                        "error": str(exc),
                    },
                )
                LOGGER.warning("WhatsApp polling error: %s", exc)
            except Exception as exc:
                self._event_log.add(
                    "whatsapp.poll.exception",
                    "WhatsApp polling exception",
                    {
                        "error": f"{exc.__class__.__name__}: {exc}",
                    },
                )
                LOGGER.exception("WhatsApp polling exception")

            time.sleep(poll_interval)

        self._event_log.add("whatsapp.loop", "WhatsApp polling loop ended", {})
        LOGGER.info("WhatsApp polling loop ended")

    def _process_message(self, message: Dict[str, Any], allowed_contacts: List[str]) -> None:
        """Process an incoming WhatsApp message."""
        try:
            contact = str(message.get("from") or "")
            text = str(message.get("text") or "").strip()

            if not contact or not text:
                return

            # Check if contact is allowed
            if allowed_contacts and contact not in allowed_contacts:
                self._event_log.add(
                    "whatsapp.denied",
                    "Ignored WhatsApp message from unauthorized contact",
                    {"contact": contact},
                )
                return

            self._event_log.add(
                "whatsapp.message.received",
                "Received WhatsApp message",
                {
                    "contact": contact,
                    "text": text,
                },
            )

            # Process with agent
            result = self._agent.chat_with_updates(
                text,
                source="whatsapp",
                meta={
                    "contact": contact,
                },
            )

            answer = str(result.get("response") or "")
            if answer:
                # Split long messages
                chunks = self._split_message(answer)
                for chunk in chunks:
                    self._send_message(contact, chunk)
                    time.sleep(0.5)  # Small delay between messages

            self._last_message_time = time.time()
            self._event_log.add(
                "whatsapp.message.sent",
                "Sent WhatsApp response",
                {
                    "contact": contact,
                    "text": answer,
                },
            )

        except Exception as exc:
            self._event_log.add(
                "whatsapp.process.error",
                "Failed to process WhatsApp message",
                {
                    "error": f"{exc.__class__.__name__}: {exc}",
                    "message": message,
                },
            )
            LOGGER.exception("Failed to process WhatsApp message")

    def _split_message(self, text: str, max_chars: int = 1600) -> List[str]:
        """Split a message into chunks that fit WhatsApp limits."""
        raw = str(text or "").strip()
        if not raw:
            return []

        chunks: List[str] = []
        remaining = raw

        while len(remaining) > max_chars:
            # Try to split at newline or sentence boundary
            split_at = remaining.rfind("\n", 0, max_chars)
            if split_at <= 0:
                split_at = remaining.rfind(". ", 0, max_chars)
            if split_at <= 0:
                split_at = remaining.rfind(" ", 0, max_chars)
            if split_at <= 0:
                split_at = max_chars

            chunks.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].strip()

        if remaining:
            chunks.append(remaining)

        return chunks
