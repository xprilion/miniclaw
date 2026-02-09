"""Unit tests for MiniClaw Telegram service."""

import json
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from miniclaw.services.telegram import (
    TelegramService,
    TelegramAPIError,
    TelegramConflictError,
)
from miniclaw.core.config import ConfigStore
from miniclaw.core.events import EventLog
from miniclaw.core.agent import MiniClawAgent


class TestTelegramService(unittest.TestCase):
    """Test cases for TelegramService."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "telegram": {
                        "enabled": True,
                        "bot_token": "test_token",
                        "allowed_chat_ids": [],
                        "pairing_required": True,
                        "pairing_code_ttl_seconds": 600,
                        "poll_interval_seconds": 2,
                        "progress_update_seconds": 12,
                    }
                }
            )
        )

        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        self.agent = Mock(spec=MiniClawAgent)
        self.agent.chat_with_updates.return_value = {"response": "test response"}

        self.telegram_service = TelegramService(
            config_store=self.config_store, event_log=self.event_log, agent=self.agent
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self):
        """Test TelegramService initialization."""
        self.assertIsInstance(self.telegram_service, TelegramService)
        self.assertEqual(self.telegram_service._offset, 0)
        self.assertIsNone(self.telegram_service._active_pairing)
        self.assertEqual(self.telegram_service._pairing_requests, {})
        self.assertEqual(self.telegram_service._next_pairing_request_id, 1)

    def test_bound_chat_id_with_allowed_chats(self):
        """Test _bound_chat_id with allowed chat IDs."""
        allowed_chat_ids = ["12345", "67890"]
        result = self.telegram_service._bound_chat_id(allowed_chat_ids)
        self.assertEqual(result, "12345")

    def test_bound_chat_id_with_empty_list(self):
        """Test _bound_chat_id with empty list."""
        allowed_chat_ids = []
        result = self.telegram_service._bound_chat_id(allowed_chat_ids)
        self.assertEqual(result, "")

    def test_chat_allowed_with_bound_chat(self):
        """Test _chat_allowed when chat is bound."""
        allowed_chat_ids = ["12345"]
        chat_id = "12345"
        pairing_required = True
        result = self.telegram_service._chat_allowed(
            chat_id, allowed_chat_ids, pairing_required
        )
        self.assertTrue(result)

    def test_chat_allowed_with_unbound_chat_and_no_pairing(self):
        """Test _chat_allowed when chat is not bound and pairing is not required."""
        allowed_chat_ids = []
        chat_id = "12345"
        pairing_required = False
        result = self.telegram_service._chat_allowed(
            chat_id, allowed_chat_ids, pairing_required
        )
        self.assertTrue(result)

    def test_chat_allowed_with_unbound_chat_and_pairing_required(self):
        """Test _chat_allowed when chat is not bound and pairing is required."""
        allowed_chat_ids = []
        chat_id = "12345"
        pairing_required = True
        result = self.telegram_service._chat_allowed(
            chat_id, allowed_chat_ids, pairing_required
        )
        self.assertFalse(result)

    def test_is_pair_command_with_valid_command(self):
        """Test _is_pair_command with valid pair command."""
        text = "/pair ABC123"
        result = self.telegram_service._is_pair_command(text)
        self.assertTrue(result)

    def test_is_pair_command_with_invalid_command(self):
        """Test _is_pair_command with invalid command."""
        text = "/start"
        result = self.telegram_service._is_pair_command(text)
        self.assertFalse(result)

    def test_extract_pair_code(self):
        """Test _extract_pair_code with valid input."""
        text = "/pair ABC123"
        result = self.telegram_service._extract_pair_code(text)
        self.assertEqual(result, "ABC123")

    def test_extract_pair_code_without_code(self):
        """Test _extract_pair_code without code."""
        text = "/pair"
        result = self.telegram_service._extract_pair_code(text)
        self.assertEqual(result, "")

    def test_create_pairing_code(self):
        """Test create_pairing_code method."""
        result = self.telegram_service.create_pairing_code(300)

        self.assertIn("code", result)
        self.assertIn("created_at", result)
        self.assertIn("expires_at", result)
        self.assertIn("ttl_seconds", result)
        self.assertEqual(result["ttl_seconds"], 300)
        self.assertEqual(len(result["code"]), 6)

    def test_status_when_not_running(self):
        """Test status method when service is not running."""
        result = self.telegram_service.status()

        self.assertFalse(result["running"])
        self.assertEqual(result["offset"], 0)
        self.assertIsNone(result["active_pairing"])
        self.assertEqual(result["pending_pairing_requests"], 0)

    def test_pairing_status(self):
        """Test pairing_status method."""
        # Create a pairing code first
        self.telegram_service.create_pairing_code(300)

        result = self.telegram_service.pairing_status()

        self.assertIn("active_pairing", result)
        self.assertIn("requests", result)
        self.assertIn("bound_chat_id", result)
        self.assertIsNotNone(result["active_pairing"])

    def test_resolve_pairing_request_with_invalid_id(self):
        """Test resolve_pairing_request with invalid request ID."""
        with self.assertRaises(ValueError) as context:
            self.telegram_service.resolve_pairing_request("", True)
        self.assertIn("request_id is required", str(context.exception))

    def test_resolve_pairing_request_with_nonexistent_id(self):
        """Test resolve_pairing_request with nonexistent request ID."""
        with self.assertRaises(ValueError) as context:
            self.telegram_service.resolve_pairing_request("nonexistent", True)
        self.assertIn("Pairing request not found", str(context.exception))

    def test_unbind_chat_when_not_bound(self):
        """Test unbind_chat when no chat is bound."""
        result = self.telegram_service.unbind_chat()
        self.assertEqual(result["removed_chat_id"], "")
        self.assertEqual(result["updated_allowed_chat_ids"], [])

    def test_split_telegram_message_empty(self):
        """Test _split_telegram_message with empty text."""
        result = self.telegram_service._split_telegram_message("")
        self.assertEqual(result, [])

    def test_split_telegram_message_short(self):
        """Test _split_telegram_message with short text."""
        text = "Short message"
        result = self.telegram_service._split_telegram_message(text)
        self.assertEqual(result, ["Short message"])

    def test_wants_multi_part_delivery_positive(self):
        """Test _wants_multi_part_delivery with positive match."""
        text = "Please send one message at a time"
        result = self.telegram_service._wants_multi_part_delivery(text)
        self.assertTrue(result)

    def test_wants_multi_part_delivery_negative(self):
        """Test _wants_multi_part_delivery with negative match."""
        text = "Send everything in one message"
        result = self.telegram_service._wants_multi_part_delivery(text)
        self.assertFalse(result)

    def test_parse_count_sequence_request_valid(self):
        """Test _parse_count_sequence_request with valid request."""
        text = "Please count from 1 to 10 one message at a time"
        result = self.telegram_service._parse_count_sequence_request(text)
        self.assertIsNotNone(result)
        self.assertEqual(result["start"], 1)
        self.assertEqual(result["end"], 10)
        self.assertEqual(result["size"], 10)

    def test_parse_count_sequence_request_invalid_range(self):
        """Test _parse_count_sequence_request with too large range."""
        text = "Please count from 1 to 300 one message at a time"
        with self.assertRaises(ValueError) as context:
            self.telegram_service._parse_count_sequence_request(text)
        self.assertIn("Count range is too large", str(context.exception))


class TestTelegramServiceWithActivePairing(unittest.TestCase):
    """Test cases for TelegramService with active pairing."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "telegram": {
                        "enabled": True,
                        "bot_token": "test_token",
                        "allowed_chat_ids": [],
                        "pairing_required": True,
                        "pairing_code_ttl_seconds": 600,
                        "poll_interval_seconds": 2,
                        "progress_update_seconds": 12,
                    }
                }
            )
        )

        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        self.agent = Mock(spec=MiniClawAgent)
        self.agent.chat_with_updates.return_value = {"response": "test response"}

        self.telegram_service = TelegramService(
            config_store=self.config_store, event_log=self.event_log, agent=self.agent
        )

        # Create an active pairing
        self.pairing_data = self.telegram_service.create_pairing_code(300)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_clean_pairing_locked_expired(self):
        """Test _clean_pairing_locked with expired pairing."""
        # Manually set expiration to past
        with self.telegram_service._lock:
            self.telegram_service._active_pairing["expires_at_epoch"] = (
                time.time() - 100
            )

        # Call clean method
        with self.telegram_service._lock:
            self.telegram_service._clean_pairing_locked()

        self.assertIsNone(self.telegram_service._active_pairing)

    def test_active_pairing_public_locked(self):
        """Test _active_pairing_public_locked with active pairing."""
        with self.telegram_service._lock:
            result = self.telegram_service._active_pairing_public_locked()

        self.assertIsNotNone(result)
        self.assertIn("code", result)
        self.assertIn("created_at", result)
        self.assertIn("expires_at", result)
        self.assertIn("ttl_seconds", result)

    def test_pairing_requests_public_locked(self):
        """Test _pairing_requests_public_locked with requests."""
        # Add a mock request
        with self.telegram_service._lock:
            self.telegram_service._pairing_requests["test-1"] = {
                "request_id": "test-1",
                "chat_id": "12345",
                "from": {"id": 12345, "username": "testuser"},
                "status": "pending",
                "requested_at": "2023-01-01T00:00:00Z",
                "resolved_at": None,
                "resolved_by": None,
            }

            result = self.telegram_service._pairing_requests_public_locked()

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["request_id"], "test-1")


class TestTelegramAPIMethods(unittest.TestCase):
    """Test cases for TelegramService API methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "telegram": {
                        "enabled": True,
                        "bot_token": "test_token",
                        "allowed_chat_ids": [],
                        "pairing_required": True,
                        "pairing_code_ttl_seconds": 600,
                        "poll_interval_seconds": 2,
                        "progress_update_seconds": 12,
                    }
                }
            )
        )

        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        self.agent = Mock(spec=MiniClawAgent)
        self.agent.chat_with_updates.return_value = {"response": "test response"}

        self.telegram_service = TelegramService(
            config_store=self.config_store, event_log=self.event_log, agent=self.agent
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("urllib.request.urlopen")
    def test_telegram_api_success(self, mock_urlopen):
        """Test _telegram_api method with successful response."""
        # Mock successful response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(
            {"ok": True, "result": "test"}
        ).encode("utf-8")
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.telegram_service._telegram_api("test_token", "getMe", {})
        self.assertEqual(result["result"], "test")

    @patch("urllib.request.urlopen")
    def test_telegram_api_error_response(self, mock_urlopen):
        """Test _telegram_api method with error response."""
        # Mock error response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(
            {"ok": False, "description": "Bad Request"}
        ).encode("utf-8")
        mock_response.status = 400
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with self.assertRaises(TelegramAPIError) as context:
            self.telegram_service._telegram_api("test_token", "getMe", {})
        self.assertIn("Bad Request", str(context.exception))

    @patch("urllib.request.urlopen")
    def test_telegram_api_http_error(self, mock_urlopen):
        """Test _telegram_api method with HTTP error."""
        import urllib.error

        # Mock HTTP error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.telegram.org/botxxx/getMe",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None,
        )

        with self.assertRaises(TelegramAPIError) as context:
            self.telegram_service._telegram_api("test_token", "getMe", {})
        self.assertEqual(context.exception.status, 404)

    @patch("urllib.request.urlopen")
    def test_telegram_api_conflict_error(self, mock_urlopen):
        """Test _telegram_api method with conflict error."""
        import urllib.error

        # Mock conflict error (HTTP 409)
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.telegram.org/botxxx/getMe",
            code=409,
            msg="Conflict",
            hdrs={},
            fp=None,
        )

        with self.assertRaises(TelegramConflictError) as context:
            self.telegram_service._telegram_api("test_token", "getMe", {})
        self.assertEqual(context.exception.status, 409)

    def test_send_message(self):
        """Test _send_message method."""
        with patch.object(self.telegram_service, "_telegram_api") as mock_api:
            self.telegram_service._send_message("test_token", "12345", "Hello")
            mock_api.assert_called_once_with(
                "test_token",
                "sendMessage",
                {
                    "chat_id": "12345",
                    "text": "Hello",
                },
            )

    def test_send_typing(self):
        """Test _send_typing method."""
        with patch.object(self.telegram_service, "_telegram_api") as mock_api:
            self.telegram_service._send_typing("test_token", "12345")
            mock_api.assert_called_once_with(
                "test_token",
                "sendChatAction",
                {
                    "chat_id": "12345",
                    "action": "typing",
                },
                timeout_seconds=10,
            )


class TestTelegramServiceIntegration(unittest.TestCase):
    """Integration test cases for TelegramService."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "telegram": {
                        "enabled": True,
                        "bot_token": "test_token",
                        "allowed_chat_ids": [],
                        "pairing_required": True,
                        "pairing_code_ttl_seconds": 600,
                        "poll_interval_seconds": 2,
                        "progress_update_seconds": 12,
                    }
                }
            )
        )

        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        self.agent = Mock(spec=MiniClawAgent)
        self.agent.chat_with_updates.return_value = {"response": "test response"}

        self.telegram_service = TelegramService(
            config_store=self.config_store, event_log=self.event_log, agent=self.agent
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_start_if_enabled_without_token(self):
        """Test start_if_enabled when token is missing."""
        # Remove token from config
        config = self.config_store.get()
        config["telegram"]["bot_token"] = ""
        self.config_store.save(config)

        # Should not start and should log error
        self.telegram_service.start_if_enabled()
        # Just verify it doesn't crash

    def test_stop_when_not_running(self):
        """Test stop method when service is not running."""
        result = self.telegram_service.stop()
        self.assertTrue(result)

    def test_restart_when_not_running(self):
        """Test restart method when service is not running."""
        result = self.telegram_service.restart()
        self.assertTrue(result)

    def test_send_test_message_without_token(self):
        """Test send_test_message when token is missing."""
        # Remove token from config
        config = self.config_store.get()
        config["telegram"]["bot_token"] = ""
        self.config_store.save(config)

        with self.assertRaises(RuntimeError) as context:
            self.telegram_service.send_test_message("12345", "test")
        self.assertIn("Telegram token is empty", str(context.exception))

    def test_handle_pair_command_with_no_code(self):
        """Test _handle_pair_command with no code provided."""
        with patch.object(self.telegram_service, "_send_message") as mock_send:
            result = self.telegram_service._handle_pair_command(
                "test_token", "12345", {"id": 12345}, "/pair"
            )
            self.assertTrue(result)  # Command was handled
            mock_send.assert_called_once()

    def test_handle_pair_command_with_invalid_code(self):
        """Test _handle_pair_command with invalid code."""
        # Create a pairing code first
        self.telegram_service.create_pairing_code(300)

        with patch.object(self.telegram_service, "_send_message") as mock_send:
            result = self.telegram_service._handle_pair_command(
                "test_token", "12345", {"id": 12345}, "/pair WRONG"
            )
            self.assertTrue(result)  # Command was handled
            mock_send.assert_called_once()


if __name__ == "__main__":
    unittest.main()
