"""Unit tests for MiniClaw WhatsApp service."""

import json
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from subprocess import CompletedProcess

from miniclaw.services.whatsapp import WhatsAppService, WhatsAppError
from miniclaw.core.config import ConfigStore
from miniclaw.core.events import EventLog
from miniclaw.core.agent import MiniClawAgent


class TestWhatsAppService(unittest.TestCase):
    """Test cases for WhatsAppService."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "channels": {
                        "whatsapp_wacli": {
                            "enabled": True,
                            "wacli_command": "wacli",
                            "allowed_contacts": ["1234567890"],
                            "poll_interval_seconds": 15,
                        }
                    }
                }
            )
        )

        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        self.agent = Mock(spec=MiniClawAgent)
        self.agent.chat_with_updates.return_value = {"response": "test response"}

        self.whatsapp_service = WhatsAppService(
            config_store=self.config_store, event_log=self.event_log, agent=self.agent
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self):
        """Test WhatsAppService initialization."""
        self.assertIsInstance(self.whatsapp_service, WhatsAppService)
        self.assertEqual(self.whatsapp_service._last_message_time, 0.0)

    def test_status_when_not_running(self):
        """Test status method when service is not running."""
        result = self.whatsapp_service.status()

        self.assertFalse(result["running"])
        self.assertTrue(result["enabled"])
        self.assertEqual(result["wacli_command"], "wacli")
        self.assertEqual(result["last_message_time"], 0.0)

    def test_send_test_message_when_disabled(self):
        """Test send_test_message when WhatsApp is disabled."""
        # Disable WhatsApp in config
        config = self.config_store.get()
        config["channels"]["whatsapp_wacli"]["enabled"] = False
        self.config_store.save(config)

        with self.assertRaises(WhatsAppError) as context:
            self.whatsapp_service.send_test_message("1234567890", "test")
        self.assertIn("WhatsApp integration is not enabled", str(context.exception))

    def test_send_test_message_without_contact(self):
        """Test send_test_message without contact."""
        with self.assertRaises(WhatsAppError) as context:
            self.whatsapp_service.send_test_message("", "test")
        self.assertIn("Contact is required", str(context.exception))

    def test_split_message_empty(self):
        """Test _split_message with empty text."""
        result = self.whatsapp_service._split_message("")
        self.assertEqual(result, [])

    def test_split_message_short(self):
        """Test _split_message with short text."""
        text = "Short message"
        result = self.whatsapp_service._split_message(text)
        self.assertEqual(result, ["Short message"])

    def test_split_message_long(self):
        """Test _split_message with long text."""
        text = "A" * 2000  # Longer than default max_chars
        result = self.whatsapp_service._split_message(text)
        self.assertGreater(len(result), 1)
        for chunk in result:
            self.assertLessEqual(len(chunk), 1600)


class TestWhatsAppAPIMethods(unittest.TestCase):
    """Test cases for WhatsAppService API methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "channels": {
                        "whatsapp_wacli": {
                            "enabled": True,
                            "wacli_command": "wacli",
                            "allowed_contacts": ["1234567890"],
                            "poll_interval_seconds": 15,
                        }
                    }
                }
            )
        )

        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        self.agent = Mock(spec=MiniClawAgent)
        self.agent.chat_with_updates.return_value = {"response": "test response"}

        self.whatsapp_service = WhatsAppService(
            config_store=self.config_store, event_log=self.event_log, agent=self.agent
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("subprocess.run")
    def test_wacli_api_success(self, mock_run):
        """Test _wacli_api method with successful response."""
        # Mock successful response
        mock_result = Mock()
        mock_result.stdout = '{"result": "test"}'
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = self.whatsapp_service._wacli_api("send", ["1234567890", "Hello"])
        self.assertEqual(result["result"], "test")

    @patch("subprocess.run")
    def test_wacli_api_success_with_text_output(self, mock_run):
        """Test _wacli_api method with text output."""
        # Mock response with text output (not JSON)
        mock_result = Mock()
        mock_result.stdout = "Plain text response"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = self.whatsapp_service._wacli_api("send", ["1234567890", "Hello"])
        self.assertEqual(result["text"], "Plain text response")

    @patch("subprocess.run")
    def test_wacli_api_timeout(self, mock_run):
        """Test _wacli_api method with timeout."""
        import subprocess

        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired("wacli send", 30)

        with self.assertRaises(WhatsAppError) as context:
            self.whatsapp_service._wacli_api("send", ["1234567890", "Hello"])
        self.assertIn("timed out", str(context.exception))

    @patch("subprocess.run")
    def test_wacli_api_called_process_error(self, mock_run):
        """Test _wacli_api method with CalledProcessError."""
        import subprocess

        # Mock called process error
        mock_error = subprocess.CalledProcessError(1, "wacli send")
        mock_error.stdout = ""
        mock_error.stderr = "Command failed"
        mock_run.side_effect = mock_error

        with self.assertRaises(WhatsAppError) as context:
            self.whatsapp_service._wacli_api("send", ["1234567890", "Hello"])
        self.assertIn("failed", str(context.exception))

    @patch("subprocess.run")
    def test_send_message(self, mock_run):
        """Test _send_message method."""
        # Mock successful response
        mock_result = Mock()
        mock_result.stdout = '{"result": "sent"}'
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        self.whatsapp_service._send_message("1234567890", "Hello")
        mock_run.assert_called_once()


class TestWhatsAppServiceIntegration(unittest.TestCase):
    """Integration test cases for WhatsAppService."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "channels": {
                        "whatsapp_wacli": {
                            "enabled": True,
                            "wacli_command": "wacli",
                            "allowed_contacts": ["1234567890"],
                            "poll_interval_seconds": 15,
                        }
                    }
                }
            )
        )

        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        self.agent = Mock(spec=MiniClawAgent)
        self.agent.chat_with_updates.return_value = {"response": "test response"}

        self.whatsapp_service = WhatsAppService(
            config_store=self.config_store, event_log=self.event_log, agent=self.agent
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_send_test_message_success(self):
        """Test send_test_message with successful send."""
        with patch.object(self.whatsapp_service, "_send_message") as mock_send:
            self.whatsapp_service.send_test_message("1234567890", "test message")
            mock_send.assert_called_once_with("1234567890", "test message")

    def test_start_if_enabled_without_command(self):
        """Test start_if_enabled when wacli command is missing."""
        # Remove wacli command from config
        config = self.config_store.get()
        config["channels"]["whatsapp_wacli"]["wacli_command"] = ""
        self.config_store.save(config)

        # Should not start and should log error
        self.whatsapp_service.start_if_enabled()
        # Just verify it doesn't crash

    def test_stop_when_not_running(self):
        """Test stop method when service is not running."""
        result = self.whatsapp_service.stop()
        self.assertTrue(result)

    def test_restart_when_not_running(self):
        """Test restart method when service is not running."""
        result = self.whatsapp_service.restart()
        self.assertTrue(result)

    @patch("subprocess.run")
    def test_process_message_from_allowed_contact(self, mock_run):
        """Test _process_message from allowed contact."""
        # Mock successful send response
        mock_result = Mock()
        mock_result.stdout = '{"result": "sent"}'
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        message = {"from": "1234567890", "text": "Hello"}

        self.whatsapp_service._process_message(message, ["1234567890"])
        # Verify that agent.chat_with_updates was called
        self.agent.chat_with_updates.assert_called_once()
        # Verify that _send_message was called
        mock_run.assert_called()

    def test_process_message_from_unauthorized_contact(self):
        """Test _process_message from unauthorized contact."""
        message = {"from": "unauthorized", "text": "Hello"}

        # Mock the event log to verify it's called
        with patch.object(self.whatsapp_service._event_log, "add") as mock_add:
            self.whatsapp_service._process_message(message, ["1234567890"])
            # Verify that unauthorized message was logged
            mock_add.assert_called_with(
                "whatsapp.denied",
                "Ignored WhatsApp message from unauthorized contact",
                {"contact": "unauthorized"},
            )

    def test_process_message_empty_fields(self):
        """Test _process_message with empty contact or text."""
        # Message with empty contact
        message1 = {"from": "", "text": "Hello"}
        self.whatsapp_service._process_message(message1, ["1234567890"])
        # Should not call agent (no exception should be raised)

        # Message with empty text
        message2 = {"from": "1234567890", "text": ""}
        self.whatsapp_service._process_message(message2, ["1234567890"])
        # Should not call agent (no exception should be raised)


if __name__ == "__main__":
    unittest.main()
