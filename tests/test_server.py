"""Unit tests for MiniClaw HTTP server."""

import json
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
from pathlib import Path

# Import the make_handler function directly
from miniclaw.services.server import make_handler


class TestServerHelpers(unittest.TestCase):
    """Test cases for server helper functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a minimal mock app state
        self.app_state = Mock()
        self.app_state.event_log = Mock()
        self.app_state.config_store = Mock()
        self.app_state.config_store.get.return_value = {
            "monitoring": {"max_events": 100},
            "agent": {"name": "Test Agent"},
            "tools": {},
            "security": {},
            "providers": {"items": [], "default_provider_id": None},
        }

        # Create the handler class
        self.handler_class = make_handler(self.app_state)

    def create_mock_handler(self, method="GET", path="/", headers=None, body=""):
        """Create a mock handler for testing."""
        if headers is None:
            headers = {}

        # Create a mock request handler
        mock_handler = Mock()
        mock_handler.command = method
        mock_handler.path = path
        mock_handler.headers = headers
        mock_handler.client_address = ("127.0.0.1", 12345)

        # Mock the wfile and rfile
        mock_handler.wfile = BytesIO()
        mock_handler.rfile = BytesIO(body.encode("utf-8"))

        # Add the methods from the actual handler
        handler_instance = self.handler_class
        mock_handler._read_body = handler_instance._read_body.__get__(
            mock_handler, handler_instance
        )
        mock_handler._read_json = handler_instance._read_json.__get__(
            mock_handler, handler_instance
        )
        mock_handler._send_json = handler_instance._send_json.__get__(
            mock_handler, handler_instance
        )
        mock_handler._send_text = handler_instance._send_text.__get__(
            mock_handler, handler_instance
        )
        mock_handler._handle_error = handler_instance._handle_error.__get__(
            mock_handler, handler_instance
        )

        return mock_handler

    def test_read_body_empty(self):
        """Test reading empty request body."""
        handler = self.create_mock_handler(body="")
        result = handler._read_body()
        self.assertEqual(result, "")

    def test_read_body_with_content(self):
        """Test reading request body with content."""
        test_content = "test request body"
        handler = self.create_mock_handler(
            headers={"Content-Length": str(len(test_content))}, body=test_content
        )
        result = handler._read_body()
        self.assertEqual(result, test_content)

    def test_read_json_valid(self):
        """Test reading valid JSON from request body."""
        test_data = {"key": "value", "number": 42}
        json_content = json.dumps(test_data)
        handler = self.create_mock_handler(
            headers={"Content-Length": str(len(json_content))}, body=json_content
        )
        result = handler._read_json()
        self.assertEqual(result, test_data)

    def test_read_json_empty(self):
        """Test reading JSON from empty body."""
        handler = self.create_mock_handler(body="")
        result = handler._read_json()
        self.assertEqual(result, {})

    def test_read_json_invalid(self):
        """Test reading invalid JSON from request body."""
        invalid_json = "{invalid json}"
        handler = self.create_mock_handler(
            headers={"Content-Length": str(len(invalid_json))}, body=invalid_json
        )
        with self.assertRaises(Exception):
            handler._read_json()

    def test_send_json(self):
        """Test sending JSON response."""
        handler = self.create_mock_handler()
        test_data = {"status": "success", "data": "test"}

        handler._send_json(test_data)

        # Check that response was written
        handler.wfile.seek(0)
        response = handler.wfile.read().decode("utf-8")
        self.assertIn("success", response)
        self.assertIn("test", response)

    def test_send_text(self):
        """Test sending text response."""
        handler = self.create_mock_handler()
        test_text = "Hello, World!"

        handler._send_text(test_text)

        # Check that response was written
        handler.wfile.seek(0)
        response = handler.wfile.read().decode("utf-8")
        self.assertIn(test_text, response)

    def test_handle_error(self):
        """Test handling errors."""
        handler = self.create_mock_handler()
        test_exception = Exception("Test error")

        handler._handle_error(test_exception, "/test/path")

        # Check that error response was sent
        handler.wfile.seek(0)
        response = handler.wfile.read().decode("utf-8")
        self.assertIn("false", response.lower())
        self.assertIn("Test error", response)


class TestServerEndpoints(unittest.TestCase):
    """Test cases for server API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a minimal mock app state
        self.app_state = Mock()
        self.app_state.event_log = Mock()
        self.app_state.config_store = Mock()
        self.app_state.config_store.get.return_value = {
            "monitoring": {"max_events": 100},
            "agent": {"name": "Test Agent"},
            "tools": {},
            "security": {},
            "providers": {"items": [], "default_provider_id": None},
        }

        # Mock all the services
        self.app_state.agent = Mock()
        self.app_state.agent.chat.return_value = {
            "response": "test response",
            "duration_seconds": 0.1,
        }
        self.app_state.agent.chat_with_updates.return_value = {
            "response": "test response",
            "duration_seconds": 0.1,
        }
        self.app_state.agent.history.return_value = []

        self.app_state.memory = Mock()
        self.app_state.memory.list_files.return_value = []
        self.app_state.memory.read_all.return_value = {}

        self.app_state.skills = Mock()
        self.app_state.skills.list.return_value = []

        self.app_state.plugins = Mock()
        self.app_state.plugins.list.return_value = []

        self.app_state.job_service = Mock()
        self.app_state.job_service.status.return_value = []

        self.app_state.telegram = Mock()
        self.app_state.telegram.status.return_value = {}
        self.app_state.telegram.pairing_status.return_value = []

        self.app_state.whatsapp = Mock()
        self.app_state.whatsapp.status.return_value = {}

        # Create the handler class
        self.handler_class = make_handler(self.app_state)

    def create_mock_handler(self, method="GET", path="/", headers=None, body=""):
        """Create a mock handler for testing."""
        if headers is None:
            headers = {}

        # Create a mock request handler
        mock_handler = Mock()
        mock_handler.command = method
        mock_handler.path = path
        mock_handler.headers = headers
        mock_handler.client_address = ("127.0.0.1", 12345)

        # Mock the wfile and rfile
        mock_handler.wfile = BytesIO()
        mock_handler.rfile = BytesIO(body.encode("utf-8"))

        # Add the methods from the actual handler
        handler_instance = self.handler_class
        mock_handler._read_body = handler_instance._read_body.__get__(
            mock_handler, handler_instance
        )
        mock_handler._read_json = handler_instance._read_json.__get__(
            mock_handler, handler_instance
        )
        mock_handler._send_json = handler_instance._send_json.__get__(
            mock_handler, handler_instance
        )
        mock_handler._send_text = handler_instance._send_text.__get__(
            mock_handler, handler_instance
        )
        mock_handler._handle_error = handler_instance._handle_error.__get__(
            mock_handler, handler_instance
        )
        mock_handler._serve_web_file = handler_instance._serve_web_file.__get__(
            mock_handler, handler_instance
        )

        # Mock do_GET and do_POST methods
        mock_handler.do_GET = handler_instance.do_GET.__get__(
            mock_handler, handler_instance
        )
        mock_handler.do_POST = handler_instance.do_POST.__get__(
            mock_handler, handler_instance
        )

        return mock_handler

    def test_health_endpoint(self):
        """Test the health check endpoint."""
        handler = self.create_mock_handler(path="/api/health")
        handler.do_GET()

        # Check that response was written
        handler.wfile.seek(0)
        response = handler.wfile.read().decode("utf-8")
        self.assertIn("true", response.lower())
        self.assertIn("timestamp", response)

    def test_config_endpoint(self):
        """Test the config endpoint."""
        handler = self.create_mock_handler(path="/api/config")
        handler.do_GET()

        # Check that response was written
        handler.wfile.seek(0)
        response = handler.wfile.read().decode("utf-8")
        self.assertIn("true", response.lower())
        self.assertIn("config", response)

    def test_memory_endpoint(self):
        """Test the memory endpoint."""
        handler = self.create_mock_handler(path="/api/memory")
        handler.do_GET()

        # Check that response was written
        handler.wfile.seek(0)
        response = handler.wfile.read().decode("utf-8")
        self.assertIn("true", response.lower())
        self.assertIn("files", response)

    def test_skills_endpoint(self):
        """Test the skills endpoint."""
        handler = self.create_mock_handler(path="/api/skills")
        handler.do_GET()

        # Check that response was written
        handler.wfile.seek(0)
        response = handler.wfile.read().decode("utf-8")
        self.assertIn("true", response.lower())
        self.assertIn("skills", response)

    def test_plugins_endpoint(self):
        """Test the plugins endpoint."""
        handler = self.create_mock_handler(path="/api/plugins")
        handler.do_GET()

        # Check that response was written
        handler.wfile.seek(0)
        response = handler.wfile.read().decode("utf-8")
        self.assertIn("true", response.lower())
        self.assertIn("plugins", response)

    def test_jobs_endpoint(self):
        """Test the jobs endpoint."""
        handler = self.create_mock_handler(path="/api/jobs")
        handler.do_GET()

        # Check that response was written
        handler.wfile.seek(0)
        response = handler.wfile.read().decode("utf-8")
        self.assertIn("true", response.lower())
        self.assertIn("jobs", response)

    def test_history_endpoint(self):
        """Test the history endpoint."""
        handler = self.create_mock_handler(path="/api/history")
        handler.do_GET()

        # Check that response was written
        handler.wfile.seek(0)
        response = handler.wfile.read().decode("utf-8")
        self.assertIn("true", response.lower())
        self.assertIn("history", response)

    def test_events_endpoint(self):
        """Test the events endpoint."""
        # Mock the event log list_since method to return serializable data
        self.app_state.event_log.list_since.return_value = []
        self.app_state.event_log.latest_id.return_value = 0

        handler = self.create_mock_handler(path="/api/events")
        handler.do_GET()

        # Check that response was written
        handler.wfile.seek(0)
        response = handler.wfile.read().decode("utf-8")
        print(f"Events response: {response}")  # Debug print
        self.assertIn("true", response.lower())
        self.assertIn("events", response)

    def test_chat_endpoint_get(self):
        """Test the chat endpoint with GET request (should return 404)."""
        handler = self.create_mock_handler(path="/api/chat")
        handler.do_GET()

        # Check that error response was sent
        handler.wfile.seek(0)
        response = handler.wfile.read().decode("utf-8")
        self.assertIn("false", response.lower())
        self.assertIn("unknown endpoint", response.lower())

    def test_chat_endpoint_post_missing_message(self):
        """Test the chat endpoint with POST request missing message."""
        handler = self.create_mock_handler(
            method="POST",
            path="/api/chat",
            headers={"Content-Type": "application/json"},
            body=json.dumps({}),
        )
        handler.do_POST()

        # Check that error response was sent
        handler.wfile.seek(0)
        response = handler.wfile.read().decode("utf-8")
        self.assertIn("false", response.lower())
        self.assertIn("message is required", response)

    def test_chat_endpoint_post_success(self):
        """Test the chat endpoint with successful POST request."""
        json_content = json.dumps({"message": "Hello, bot!"})
        handler = self.create_mock_handler(
            method="POST",
            path="/api/chat",
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(json_content)),
            },
            body=json_content,
        )
        handler.do_POST()

        # Check that response was written
        handler.wfile.seek(0)
        response = handler.wfile.read().decode("utf-8")
        print(f"Response: {response}")  # Debug print
        self.assertIn("true", response.lower())
        # Note: The actual response content depends on how the mock is set up

    def test_unknown_endpoint(self):
        """Test requesting an unknown endpoint."""
        handler = self.create_mock_handler(path="/api/unknown")
        handler.do_GET()

        # Check that error response was sent
        handler.wfile.seek(0)
        response = handler.wfile.read().decode("utf-8")
        self.assertIn("false", response.lower())
        self.assertIn("unknown endpoint", response.lower())


if __name__ == "__main__":
    unittest.main()
