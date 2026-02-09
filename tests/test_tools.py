"""Unit tests for MiniClaw tools."""

import json
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from miniclaw.tools.tools import ToolRunner
from miniclaw.core.config import ConfigStore
from miniclaw.core.events import EventLog
from miniclaw.services.mcp import MCPServerManager


class TestToolRunner(unittest.TestCase):
    """Test cases for ToolRunner."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "tools": {
                        "enabled": True,
                        "allow_shell": True,
                        "allow_filesystem": True,
                        "allow_network": True,
                        "allow_browser": True,
                        "allow_mcp": True,
                        "working_directory": self.temp_dir,
                    }
                }
            )
        )

        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        self.mcp = Mock(spec=MCPServerManager)

        # Create a mock security manager
        self.security_managers = {
            "permissions": Mock(),
            "rate_limiter": Mock(),
            "content_filter": Mock(),
            "sandbox": Mock(),
        }

        # Mock permission checks to allow all by default
        self.security_managers["permissions"].check_tool_permission.return_value = True
        self.security_managers["rate_limiter"].check_rate_limit.return_value = True
        self.security_managers["content_filter"].filter_output.side_effect = (
            lambda x, **kwargs: x
        )
        self.security_managers["sandbox"].sanitize_input.side_effect = (
            lambda x, **kwargs: x
        )
        self.security_managers["sandbox"].validate_command.return_value = True
        self.security_managers["sandbox"].validate_file_path.return_value = True

        self.tool_runner = ToolRunner(
            config_store=self.config_store,
            event_log=self.event_log,
            mcp=self.mcp,
            security_managers=self.security_managers,
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_catalog_with_all_tools_enabled(self):
        """Test catalog method with all tools enabled."""
        catalog = self.tool_runner.catalog()

        self.assertTrue(catalog["enabled"])
        self.assertIsInstance(catalog["tools"], list)
        self.assertGreater(len(catalog["tools"]), 0)

        # Check that all expected tools are present
        tool_names = [tool["name"] for tool in catalog["tools"]]
        expected_tools = [
            "run_command",
            "list_dir",
            "read_file",
            "write_file",
            "fetch_url",
            "browser_extract",
        ]
        for tool in expected_tools:
            self.assertIn(tool, tool_names)

    def test_catalog_with_tools_disabled(self):
        """Test catalog method with tools disabled."""
        # Update config to disable tools
        config = self.config_store.get()
        config["tools"]["enabled"] = False
        self.config_store.save(config)

        catalog = self.tool_runner.catalog()
        self.assertFalse(catalog["enabled"])
        self.assertEqual(len(catalog["tools"]), 0)

    def test_catalog_with_shell_disabled(self):
        """Test catalog method with shell commands disabled."""
        # Update config to disable shell commands
        config = self.config_store.get()
        config["tools"]["allow_shell"] = False
        self.config_store.save(config)

        catalog = self.tool_runner.catalog()
        tool_names = [tool["name"] for tool in catalog["tools"]]
        self.assertNotIn("run_command", tool_names)

    def test_catalog_with_filesystem_disabled(self):
        """Test catalog method with filesystem operations disabled."""
        # Update config to disable filesystem operations
        config = self.config_store.get()
        config["tools"]["allow_filesystem"] = False
        self.config_store.save(config)

        catalog = self.tool_runner.catalog()
        tool_names = [tool["name"] for tool in catalog["tools"]]
        self.assertNotIn("list_dir", tool_names)
        self.assertNotIn("read_file", tool_names)
        self.assertNotIn("write_file", tool_names)

    def test_agent_prompt_block(self):
        """Test agent prompt block generation."""
        prompt = self.tool_runner.agent_prompt_block()

        self.assertIsInstance(prompt, str)
        self.assertIn("tools", prompt.lower())
        self.assertIn("run_command", prompt)
        self.assertIn("list_dir", prompt)
        self.assertIn("read_file", prompt)

    def test_tool_defs_ollama(self):
        """Test Ollama tool definitions generation."""
        tool_defs = self.tool_runner.tool_defs_ollama()

        self.assertIsInstance(tool_defs, list)
        self.assertGreater(len(tool_defs), 0)

        # Check structure of first tool definition
        first_tool = tool_defs[0]
        self.assertIn("type", first_tool)
        self.assertIn("function", first_tool)
        self.assertIn("name", first_tool["function"])
        self.assertIn("description", first_tool["function"])
        self.assertIn("parameters", first_tool["function"])

    def test_parse_tool_call_valid_json(self):
        """Test parsing valid tool call JSON."""
        json_text = '{"tool": "list_dir", "arguments": {"path": "/home"}}'
        result = self.tool_runner.parse_tool_call(json_text)

        self.assertIsNotNone(result)
        self.assertEqual(result["tool"], "list_dir")
        self.assertEqual(result["arguments"], {"path": "/home"})

    def test_parse_tool_call_invalid_json(self):
        """Test parsing invalid tool call JSON."""
        invalid_json = "not valid json"
        result = self.tool_runner.parse_tool_call(invalid_json)
        self.assertIsNone(result)

    def test_parse_tool_call_missing_tool_name(self):
        """Test parsing tool call JSON missing tool name."""
        json_text = '{"arguments": {"path": "/home"}}'
        result = self.tool_runner.parse_tool_call(json_text)
        self.assertIsNone(result)

    def test_parse_tool_call_no_arguments(self):
        """Test parsing tool call JSON with no arguments."""
        json_text = '{"tool": "list_dir"}'
        result = self.tool_runner.parse_tool_call(json_text)

        self.assertIsNotNone(result)
        self.assertEqual(result["tool"], "list_dir")
        self.assertEqual(result["arguments"], {})

    def test_resolve_workdir_default(self):
        """Test resolving work directory with default path."""
        workdir = self.tool_runner._resolve_workdir()
        self.assertIsInstance(workdir, Path)
        # Should resolve to the configured working directory
        self.assertEqual(str(workdir), self.temp_dir)

    def test_resolve_workdir_relative_path(self):
        """Test resolving work directory with relative path."""
        workdir = self.tool_runner._resolve_workdir("subdir")
        self.assertIsInstance(workdir, Path)
        # Should resolve to base directory + relative path
        expected = (Path(self.temp_dir) / "subdir").resolve()
        self.assertEqual(workdir, expected)

    def test_resolve_workdir_absolute_path(self):
        """Test resolving work directory with absolute path."""
        abs_path = "/tmp/test"
        workdir = self.tool_runner._resolve_workdir(abs_path)
        self.assertIsInstance(workdir, Path)
        # Should resolve to the absolute path
        self.assertEqual(str(workdir), abs_path)

    def test_allow_feature_enabled(self):
        """Test allow method with feature enabled."""
        result = self.tool_runner._allow("allow_shell", True)
        self.assertTrue(result)

    def test_allow_feature_disabled(self):
        """Test allow method with feature disabled."""
        # Update config to disable the feature
        config = self.config_store.get()
        config["tools"]["allow_shell"] = False
        self.config_store.save(config)

        result = self.tool_runner._allow("allow_shell", True)
        self.assertFalse(result)

    def test_allow_tools_globally_disabled(self):
        """Test allow method with tools globally disabled."""
        # Update config to disable tools
        config = self.config_store.get()
        config["tools"]["enabled"] = False
        self.config_store.save(config)

        result = self.tool_runner._allow("allow_shell", True)
        self.assertFalse(result)

    def test_args_schema_to_parameters_basic(self):
        """Test converting args schema to parameters."""
        args_schema = {"command": "string", "cwd": "string(optional)"}
        result = self.tool_runner._args_schema_to_parameters(args_schema)

        self.assertIsInstance(result, dict)
        self.assertIn("type", result)
        self.assertIn("properties", result)
        self.assertIn("required", result)
        self.assertEqual(result["type"], "object")
        self.assertIn("command", result["properties"])
        self.assertIn("cwd", result["properties"])
        self.assertIn("command", result["required"])
        self.assertNotIn("cwd", result["required"])

    def test_args_schema_to_parameters_empty(self):
        """Test converting empty args schema to parameters."""
        result = self.tool_runner._args_schema_to_parameters({})
        self.assertIsInstance(result, dict)
        self.assertEqual(result["type"], "object")
        self.assertEqual(result["properties"], {})
        self.assertEqual(result["required"], [])

    def test_run_unknown_tool(self):
        """Test running an unknown tool."""
        result = self.tool_runner.run("unknown_tool", {})
        # Should return error result rather than raising exception
        self.assertFalse(result["ok"])
        self.assertIn("Unknown tool", result["error"])


class TestToolRunnerWithPermissions(unittest.TestCase):
    """Test cases for ToolRunner with permission checks."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "tools": {
                        "enabled": True,
                        "allow_shell": True,
                        "allow_filesystem": True,
                        "allow_network": True,
                        "allow_browser": True,
                        "allow_mcp": True,
                        "working_directory": self.temp_dir,
                    }
                }
            )
        )

        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        self.mcp = Mock(spec=MCPServerManager)

        # Create a mock security manager
        self.security_managers = {
            "permissions": Mock(),
            "rate_limiter": Mock(),
            "content_filter": Mock(),
            "sandbox": Mock(),
        }

        self.tool_runner = ToolRunner(
            config_store=self.config_store,
            event_log=self.event_log,
            mcp=self.mcp,
            security_managers=self.security_managers,
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_run_tool_permission_denied(self):
        """Test running a tool when permission is denied."""
        # Mock permission check to deny access
        self.security_managers["permissions"].check_tool_permission.return_value = False

        with self.assertRaises(PermissionError) as context:
            self.tool_runner.run("list_dir", {"path": "."})
        self.assertIn("Permission denied", str(context.exception))

    def test_run_tool_rate_limit_exceeded(self):
        """Test running a tool when rate limit is exceeded."""
        # Mock permission check to allow access
        self.security_managers["permissions"].check_tool_permission.return_value = True
        # Mock rate limiter to deny access
        self.security_managers["rate_limiter"].check_rate_limit.return_value = False

        with self.assertRaises(PermissionError) as context:
            self.tool_runner.run("list_dir", {"path": "."})
        self.assertIn("Rate limit exceeded", str(context.exception))


if __name__ == "__main__":
    unittest.main()
