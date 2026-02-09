"""Unit tests for MiniClaw MCP service."""

import json
import tempfile
import time
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from subprocess import Popen

from miniclaw.services.mcp import MCPStdioSession, MCPServerManager
from miniclaw.core.config import ConfigStore
from miniclaw.core.events import EventLog


class TestMCPStdioSession(unittest.TestCase):
    """Test cases for MCPStdioSession."""

    def setUp(self):
        """Set up test fixtures."""
        self.server_config = {
            "id": "test-server",
            "command": "echo",
            "args": ["test"],
            "transport": "stdio",
            "enabled": True,
            "timeout_seconds": 30,
        }
        self.session = MCPStdioSession(self.server_config)

    def test_init(self):
        """Test MCPStdioSession initialization."""
        self.assertIsInstance(self.session, MCPStdioSession)
        self.assertEqual(self.session.server["id"], "test-server")
        self.assertIsNone(self.session._process)
        self.assertEqual(self.session._next_id, 1)

    def test_build_command_with_simple_command(self):
        """Test _build_command with simple command."""
        result = self.session._build_command()
        self.assertEqual(result, ["echo", "test"])

    def test_build_command_without_command(self):
        """Test _build_command without command."""
        self.session.server["command"] = ""
        with self.assertRaises(ValueError) as context:
            self.session._build_command()
        self.assertIn("has no command configured", str(context.exception))

    def test_build_command_with_complex_command(self):
        """Test _build_command with complex command."""
        self.session.server["command"] = "python -c"
        self.session.server["args"] = ["\"print('hello')\""]
        result = self.session._build_command()
        self.assertEqual(result, ["python", "-c", "\"print('hello')\""])

    def test_start_when_already_started(self):
        """Test start method when already started."""
        # Mock a process
        mock_process = Mock()
        mock_process.poll.return_value = None
        self.session._process = mock_process

        # Should not start again
        self.session.start()
        # Verify that no new process was created
        self.assertEqual(self.session._process, mock_process)

    def test_stop_when_not_started(self):
        """Test stop method when not started."""
        # Should not raise exception
        self.session.stop()
        self.assertIsNone(self.session._process)

    @patch("subprocess.Popen")
    def test_stop_with_running_process(self, mock_popen):
        """Test stop method with running process."""
        # Mock a running process
        mock_process = Mock()
        mock_process.poll.return_value = None  # Still running
        mock_popen.return_value = mock_process

        # Start the session
        self.session.start()

        # Stop the session
        self.session.stop()
        # Verify terminate was called
        mock_process.terminate.assert_called_once()
        self.assertIsNone(self.session._process)

    def test_stdout_when_not_started(self):
        """Test _stdout method when not started."""
        with self.assertRaises(RuntimeError) as context:
            self.session._stdout()
        self.assertIn("MCP process is not started", str(context.exception))

    def test_stdin_when_not_started(self):
        """Test _stdin method when not started."""
        with self.assertRaises(RuntimeError) as context:
            self.session._stdin()
        self.assertIn("MCP process is not started", str(context.exception))

    def test_notify(self):
        """Test notify method."""
        with patch.object(self.session, "_send") as mock_send:
            self.session.notify("test_method", {"key": "value"})
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            self.assertEqual(args[0]["method"], "test_method")
            self.assertEqual(args[0]["params"], {"key": "value"})

    def test_request(self):
        """Test request method."""
        with (
            patch.object(self.session, "_send") as mock_send,
            patch.object(self.session, "_read_message") as mock_read,
        ):
            # Mock response
            mock_read.return_value = {"id": 1, "result": {"test": "value"}}

            result = self.session.request("test_method", {"key": "value"})
            mock_send.assert_called_once()
            mock_read.assert_called_once()
            self.assertEqual(result, {"test": "value"})

    def test_request_with_error_response(self):
        """Test request method with error response."""
        with (
            patch.object(self.session, "_send"),
            patch.object(self.session, "_read_message") as mock_read,
        ):
            # Mock error response
            mock_read.return_value = {"id": 1, "error": {"message": "Test error"}}

            with self.assertRaises(RuntimeError) as context:
                self.session.request("test_method", {"key": "value"})
            self.assertIn("MCP error", str(context.exception))

    def test_initialize(self):
        """Test initialize method."""
        with (
            patch.object(self.session, "request") as mock_request,
            patch.object(self.session, "notify") as mock_notify,
        ):
            # Mock successful initialization
            mock_request.return_value = {"capabilities": {}}

            result = self.session.initialize()
            mock_request.assert_called_once()
            # Verify notify was called (may raise exception which is caught)
            mock_notify.assert_called_once_with("notifications/initialized", {})
            self.assertEqual(result, {"capabilities": {}})


class TestMCPServerManager(unittest.TestCase):
    """Test cases for MCPServerManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "mcp": {
                        "enabled": True,
                        "servers": [
                            {
                                "id": "test-server",
                                "command": "echo",
                                "args": ["test"],
                                "transport": "stdio",
                                "enabled": True,
                                "timeout_seconds": 30,
                            }
                        ],
                    }
                }
            )
        )

        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        self.mcp_manager = MCPServerManager(
            config_store=self.config_store, event_log=self.event_log
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self):
        """Test MCPServerManager initialization."""
        self.assertIsInstance(self.mcp_manager, MCPServerManager)

    def test_list_servers(self):
        """Test list_servers method."""
        result = self.mcp_manager.list_servers()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "test-server")

    def test_find_server_success(self):
        """Test _find_server method with existing server."""
        result = self.mcp_manager._find_server("test-server")
        self.assertEqual(result["id"], "test-server")

    def test_find_server_not_found(self):
        """Test _find_server method with non-existent server."""
        with self.assertRaises(ValueError) as context:
            self.mcp_manager._find_server("non-existent")
        self.assertIn("MCP server not found", str(context.exception))

    def test_session_for_disabled_server(self):
        """Test _session_for method with disabled server."""
        # Add a disabled server to config
        config = self.config_store.get()
        config["mcp"]["servers"].append(
            {
                "id": "disabled-server",
                "command": "echo",
                "args": ["test"],
                "transport": "stdio",
                "enabled": False,
            }
        )
        self.config_store.save(config)

        with self.assertRaises(ValueError) as context:
            self.mcp_manager._session_for("disabled-server")
        self.assertIn("MCP server is disabled", str(context.exception))

    def test_session_for_unsupported_transport(self):
        """Test _session_for method with unsupported transport."""
        # Add a server with unsupported transport
        config = self.config_store.get()
        config["mcp"]["servers"].append(
            {
                "id": "unsupported-server",
                "command": "echo",
                "args": ["test"],
                "transport": "http",
                "enabled": True,
            }
        )
        self.config_store.save(config)

        with self.assertRaises(ValueError) as context:
            self.mcp_manager._session_for("unsupported-server")
        self.assertIn("Unsupported MCP transport", str(context.exception))

    def test_session_for_empty_command(self):
        """Test _session_for method with empty command."""
        # Add a server with empty command
        config = self.config_store.get()
        config["mcp"]["servers"].append(
            {
                "id": "empty-command-server",
                "command": "",
                "args": ["test"],
                "transport": "stdio",
                "enabled": True,
            }
        )
        self.config_store.save(config)

        with self.assertRaises(ValueError) as context:
            self.mcp_manager._session_for("empty-command-server")
        self.assertIn("MCP server command is empty", str(context.exception))

    def test_session_for_success(self):
        """Test _session_for method with valid server."""
        session = self.mcp_manager._session_for("test-server")
        self.assertIsInstance(session, MCPStdioSession)
        self.assertEqual(session.server["id"], "test-server")

    @patch("miniclaw.services.mcp.MCPStdioSession")
    def test_test_server_success(self, mock_session_class):
        """Test test_server method with successful test."""
        # Mock session
        mock_session = Mock()
        mock_session.server = {"timeout_seconds": 30}
        mock_session.initialize.return_value = {"capabilities": {}}
        mock_session_class.return_value = mock_session

        result = self.mcp_manager.test_server("test-server")
        self.assertTrue(result["ok"])
        self.assertEqual(result["server_id"], "test-server")
        self.assertIn("duration_seconds", result)
        self.assertIn("initialize", result)

    @patch("miniclaw.services.mcp.MCPStdioSession")
    def test_test_server_failure(self, mock_session_class):
        """Test test_server method with failure."""
        # Mock session that raises exception
        mock_session = Mock()
        mock_session.server = {"timeout_seconds": 30}
        mock_session.initialize.side_effect = RuntimeError("Test error")
        mock_session_class.return_value = mock_session

        with self.assertRaises(RuntimeError) as context:
            self.mcp_manager.test_server("test-server")
        self.assertIn("Test error", str(context.exception))
        # Verify session.stop was called even with exception
        mock_session.stop.assert_called_once()

    @patch("miniclaw.services.mcp.MCPStdioSession")
    def test_list_tools_success(self, mock_session_class):
        """Test list_tools method with successful response."""
        # Mock session
        mock_session = Mock()
        mock_session.server = {"timeout_seconds": 30}
        mock_session.initialize.return_value = None
        mock_session.request.return_value = {"tools": [{"name": "test-tool"}]}
        mock_session_class.return_value = mock_session

        result = self.mcp_manager.list_tools("test-server")
        self.assertEqual(result["server_id"], "test-server")
        self.assertEqual(result["tools"], [{"name": "test-tool"}])
        self.assertEqual(result["count"], 1)

    @patch("miniclaw.services.mcp.MCPStdioSession")
    def test_list_tools_invalid_response(self, mock_session_class):
        """Test list_tools method with invalid response."""
        # Mock session with invalid tools response
        mock_session = Mock()
        mock_session.server = {"timeout_seconds": 30}
        mock_session.initialize.return_value = None
        mock_session.request.return_value = {"tools": "invalid"}
        mock_session_class.return_value = mock_session

        result = self.mcp_manager.list_tools("test-server")
        self.assertEqual(result["server_id"], "test-server")
        self.assertEqual(result["tools"], [])
        self.assertEqual(result["count"], 0)

    @patch("miniclaw.services.mcp.MCPStdioSession")
    def test_call_tool_success(self, mock_session_class):
        """Test call_tool method with successful response."""
        # Mock session
        mock_session = Mock()
        mock_session.server = {"timeout_seconds": 30}
        mock_session.initialize.return_value = None
        mock_session.request.return_value = {"result": "test-result"}
        mock_session_class.return_value = mock_session

        result = self.mcp_manager.call_tool(
            "test-server", "test-tool", {"arg": "value"}
        )
        self.assertEqual(result["server_id"], "test-server")
        self.assertEqual(result["tool_name"], "test-tool")
        self.assertEqual(result["result"], {"result": "test-result"})

    def test_call_tool_without_name(self):
        """Test call_tool method without tool name."""
        with self.assertRaises(ValueError) as context:
            self.mcp_manager.call_tool("test-server", "", {"arg": "value"})
        self.assertIn("tool_name is required", str(context.exception))

    @patch("miniclaw.services.mcp.MCPStdioSession")
    def test_call_tool_with_none_arguments(self, mock_session_class):
        """Test call_tool method with None arguments."""
        # Mock session
        mock_session = Mock()
        mock_session.server = {"timeout_seconds": 30}
        mock_session.initialize.return_value = None
        mock_session.request.return_value = {"result": "test-result"}
        mock_session_class.return_value = mock_session

        result = self.mcp_manager.call_tool("test-server", "test-tool", None)
        self.assertEqual(result["server_id"], "test-server")
        self.assertEqual(result["tool_name"], "test-tool")


if __name__ == "__main__":
    unittest.main()
