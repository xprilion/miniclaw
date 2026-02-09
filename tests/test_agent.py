"""Unit tests for MiniClaw agent."""

import json
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from miniclaw.core.agent import MiniClawAgent
from miniclaw.core.config import ConfigStore
from miniclaw.core.events import EventLog, UsageTracker
from miniclaw.data.memory_store import MemoryStore
from miniclaw.tools.model_client import ModelProviderClient
from miniclaw.plugins.plugins import PluginRegistry
from miniclaw.tools.skills import SkillRegistry
from miniclaw.tools.tools import ToolRunner


class TestMiniClawAgent(unittest.TestCase):
    """Test cases for MiniClawAgent."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "agent": {
                        "name": "Test Agent",
                        "enabled_skills": [],
                        "skill_match_min_score": 2,
                        "max_history_messages": 12,
                        "system_prompt_default": "You are MiniClaw.",
                    },
                    "providers": {
                        "items": [
                            {
                                "id": "test_provider",
                                "type": "ollama",
                                "model": "test-model",
                                "enabled": True,
                            }
                        ],
                        "default_provider_id": "test_provider",
                    },
                    "tools": {
                        "enabled": True,
                        "allow_shell": True,
                        "allow_filesystem": True,
                        "allow_network": True,
                        "allow_browser": True,
                        "allow_mcp": True,
                        "working_directory": self.temp_dir,
                    },
                }
            )
        )

        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        self.skill_registry = Mock(spec=SkillRegistry)
        self.plugin_registry = Mock(spec=PluginRegistry)
        self.model_client = Mock(spec=ModelProviderClient)
        self.usage_tracker = Mock(spec=UsageTracker)
        self.memory_store = Mock(spec=MemoryStore)
        self.tool_runner = Mock(spec=ToolRunner)

        # Mock the plugin registry methods
        self.plugin_registry.list.return_value = []
        self.plugin_registry.run_pre_prompt.return_value = []
        self.plugin_registry.run_post_response.return_value = []

        # Mock the skill registry methods
        self.skill_registry.applicable_for_query.return_value = []

        # Mock the memory store methods
        self.memory_store.prompt_blocks.return_value = []
        self.memory_store.append_journal.return_value = None

        # Mock the tool runner methods
        self.tool_runner.catalog.return_value = {
            "enabled": False,
            "tools": [],
            "max_steps": 0,
        }
        self.tool_runner.parse_tool_call.return_value = None

        # Mock the model client to return a simple response
        self.model_client.chat.return_value = {
            "message": {"content": "Test response"},
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            "provider_id": "test_provider",
            "provider_type": "ollama",
            "model": "test-model",
        }

        self.agent = MiniClawAgent(
            config_store=self.config_store,
            event_log=self.event_log,
            skill_registry=self.skill_registry,
            plugin_registry=self.plugin_registry,
            model_client=self.model_client,
            usage_tracker=self.usage_tracker,
            memory_store=self.memory_store,
            tool_runner=self.tool_runner,
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_history_empty(self):
        """Test history method with empty history."""
        history = self.agent.history()
        self.assertEqual(history, [])

    def test_history_with_messages(self):
        """Test history method with messages."""
        # Add some messages to history by calling chat
        with patch.object(self.agent, "_chat_lock"):
            self.agent._history.append(
                {
                    "role": "user",
                    "content": "Hello",
                    "source": "test",
                    "timestamp": "2023-01-01T00:00:00Z",
                }
            )
            self.agent._history.append(
                {
                    "role": "assistant",
                    "content": "Hi there!",
                    "source": "miniclaw",
                    "timestamp": "2023-01-01T00:00:01Z",
                }
            )

        history = self.agent.history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["content"], "Hello")
        self.assertEqual(history[1]["content"], "Hi there!")

    def test_history_with_limit(self):
        """Test history method with limit."""
        # Add more messages than the limit
        with patch.object(self.agent, "_chat_lock"):
            for i in range(10):
                self.agent._history.append(
                    {
                        "role": "user",
                        "content": f"Message {i}",
                        "source": "test",
                        "timestamp": f"2023-01-01T00:00:{i:02d}Z",
                    }
                )

        history = self.agent.history(limit=5)
        self.assertEqual(len(history), 5)
        # Should return the most recent 5 messages
        self.assertEqual(history[0]["content"], "Message 5")
        self.assertEqual(history[4]["content"], "Message 9")

    def test_chat_with_empty_message(self):
        """Test chat method with empty message."""
        with self.assertRaises(ValueError) as context:
            self.agent.chat("")
        self.assertIn("Message must not be empty", str(context.exception))

    def test_chat_with_whitespace_only_message(self):
        """Test chat method with whitespace-only message."""
        with self.assertRaises(ValueError) as context:
            self.agent.chat("   \n\t  ")
        self.assertIn("Message must not be empty", str(context.exception))

    def test_chat_success(self):
        """Test successful chat interaction."""
        response = self.agent.chat("Hello, bot!")

        # Check that response has expected structure
        self.assertIn("response", response)
        self.assertIn("provider", response)
        self.assertIn("usage", response)
        self.assertIn("model_calls", response)
        self.assertIn("tool_runs", response)

        # Check specific values
        self.assertEqual(response["response"], "Test response")
        self.assertEqual(response["model_calls"], 1)
        self.assertEqual(response["tool_runs"], [])

        # Check that model client was called
        self.model_client.chat.assert_called_once()

        # Check that history was updated
        history = self.agent.history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "Hello, bot!")
        self.assertEqual(history[1]["role"], "assistant")
        self.assertEqual(history[1]["content"], "Test response")

    def test_chat_with_source_and_meta(self):
        """Test chat method with source and meta parameters."""
        meta = {"test_key": "test_value"}
        response = self.agent.chat("Hello, bot!", source="cli", meta=meta)

        # Check that response was generated
        self.assertIn("response", response)
        self.assertEqual(response["response"], "Test response")

        # Check that history includes source and meta
        history = self.agent.history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["source"], "cli")
        self.assertEqual(history[0]["meta"], meta)

    def test_resolve_provider_no_providers(self):
        """Test resolve_provider with no providers configured."""
        # Update config to have no providers
        config = self.config_store.get()
        config["providers"]["items"] = []
        self.config_store.save(config)

        with self.assertRaises(RuntimeError) as context:
            # Call private method directly for testing
            self.agent._resolve_provider(config)
        self.assertIn("No model providers are configured", str(context.exception))

    def test_resolve_provider_no_enabled_providers(self):
        """Test resolve_provider with no enabled providers."""
        # Update config to have disabled providers
        config = self.config_store.get()
        config["providers"]["items"] = [
            {
                "id": "disabled_provider",
                "type": "ollama",
                "model": "test-model",
                "enabled": False,
            }
        ]
        self.config_store.save(config)

        with self.assertRaises(RuntimeError) as context:
            self.agent._resolve_provider(config)
        self.assertIn(
            "No enabled model providers are available", str(context.exception)
        )

    def test_resolve_provider_default_provider(self):
        """Test resolve_provider with default provider."""
        config = self.config_store.get()
        provider, reason = self.agent._resolve_provider(config)

        self.assertEqual(provider["id"], "test_provider")
        self.assertEqual(provider["type"], "ollama")
        self.assertEqual(provider["model"], "test-model")
        self.assertEqual(reason, "default")

    def test_resolve_provider_requested_provider(self):
        """Test resolve_provider with requested provider."""
        config = self.config_store.get()
        provider, reason = self.agent._resolve_provider(
            config, requested_provider_id="test_provider"
        )

        self.assertEqual(provider["id"], "test_provider")
        self.assertEqual(reason, "requested")

    def test_resolve_provider_missing_requested_provider(self):
        """Test resolve_provider with missing requested provider."""
        config = self.config_store.get()
        provider, reason = self.agent._resolve_provider(
            config, requested_provider_id="missing_provider"
        )

        # Should fall back to default provider
        self.assertEqual(provider["id"], "test_provider")
        self.assertIn("requested_missing", reason)


class TestMiniClawAgentWithTools(unittest.TestCase):
    """Test cases for MiniClawAgent with tool usage."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "agent": {
                        "name": "Test Agent",
                        "enabled_skills": [],
                        "skill_match_min_score": 2,
                        "max_history_messages": 12,
                        "system_prompt_default": "You are MiniClaw.",
                    },
                    "providers": {
                        "items": [
                            {
                                "id": "test_provider",
                                "type": "ollama",
                                "model": "test-model",
                                "enabled": True,
                            }
                        ],
                        "default_provider_id": "test_provider",
                    },
                    "tools": {
                        "enabled": True,
                        "allow_shell": True,
                        "allow_filesystem": True,
                        "allow_network": True,
                        "allow_browser": True,
                        "allow_mcp": True,
                        "working_directory": self.temp_dir,
                        "max_steps": 5,
                    },
                }
            )
        )

        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        self.skill_registry = Mock(spec=SkillRegistry)
        self.plugin_registry = Mock(spec=PluginRegistry)
        self.model_client = Mock(spec=ModelProviderClient)
        self.usage_tracker = Mock(spec=UsageTracker)
        self.memory_store = Mock(spec=MemoryStore)
        self.tool_runner = Mock(spec=ToolRunner)

        # Mock the plugin registry methods
        self.plugin_registry.list.return_value = []
        self.plugin_registry.run_pre_prompt.return_value = []
        self.plugin_registry.run_post_response.return_value = []

        # Mock the skill registry methods
        self.skill_registry.applicable_for_query.return_value = []

        # Mock the memory store methods
        self.memory_store.prompt_blocks.return_value = []
        self.memory_store.append_journal.return_value = None

        # Mock the tool runner methods
        self.tool_runner.catalog.return_value = {
            "enabled": True,
            "tools": [{"name": "list_dir", "description": "List directory contents"}],
            "max_steps": 5,
        }
        self.tool_runner.agent_prompt_block.return_value = "Tool instructions"
        self.tool_runner.parse_tool_call.return_value = None

        # Mock the model client to return a simple response
        self.model_client.chat.return_value = {
            "message": {"content": "Test response"},
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            "provider_id": "test_provider",
            "provider_type": "ollama",
            "model": "test-model",
        }

        self.agent = MiniClawAgent(
            config_store=self.config_store,
            event_log=self.event_log,
            skill_registry=self.skill_registry,
            plugin_registry=self.plugin_registry,
            model_client=self.model_client,
            usage_tracker=self.usage_tracker,
            memory_store=self.memory_store,
            tool_runner=self.tool_runner,
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_chat_with_tools_enabled(self):
        """Test chat with tools enabled."""
        response = self.agent.chat("List directory contents")

        # Check that response was generated
        self.assertIn("response", response)
        self.assertEqual(response["response"], "Test response")

        # Check that model client was called (should be called once)
        self.assertEqual(self.model_client.chat.call_count, 1)

        # Check that tool runner catalog was called
        self.tool_runner.catalog.assert_called_once()


if __name__ == "__main__":
    unittest.main()
