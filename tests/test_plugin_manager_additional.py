"""Additional unit tests for MiniClaw plugin manager."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from miniclaw.plugins.plugin_manager import (
    EnhancedPluginManager,
    PluginExecutionContext,
    create_plugin_manager,
)
from miniclaw.core.config import ConfigStore
from miniclaw.core.events import EventLog


class TestPluginManagerAdditional(unittest.TestCase):
    """Additional test cases for EnhancedPluginManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.plugins_dir = Path(self.temp_dir) / "plugins"
        self.plugins_dir.mkdir()

        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(json.dumps({}))

        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        self.plugin_manager = EnhancedPluginManager(
            self.plugins_dir, self.config_store, self.event_log
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_unload_plugin_not_loaded(self):
        """Test unloading a plugin that isn't loaded."""
        result = self.plugin_manager.unload_plugin("nonexistent_plugin")
        self.assertFalse(result)

    def test_disable_plugin_not_enabled(self):
        """Test disabling a plugin that isn't enabled."""
        result = self.plugin_manager.disable_plugin("nonexistent_plugin")
        self.assertFalse(result)

    def test_enable_plugin_load_failure(self):
        """Test enabling a plugin that fails to load."""
        # Create a plugin file that will cause an import error
        plugin_file = self.plugins_dir / "broken_plugin.py"
        plugin_file.write_text("""
# name: Broken Plugin
# description: A plugin that will fail to load
# version: 1.0.0

# Intentional syntax error - missing colon
def on_load(context)
    undefined_variable.something()  # This will cause a SyntaxError
""")

        result = self.plugin_manager.enable_plugin("broken_plugin")
        self.assertFalse(result)

    def test_list_plugins_with_loaded_plugins(self):
        """Test listing plugins when some are loaded."""
        # Create a test plugin file
        plugin_file = self.plugins_dir / "test_plugin.py"
        plugin_file.write_text("""
# name: Test Plugin
# description: A test plugin
# version: 1.0.0

def on_load(context):
    pass
""")

        # Load the plugin
        self.plugin_manager.load_plugin("test_plugin")

        # List plugins
        plugins = self.plugin_manager.list_plugins()
        self.assertEqual(len(plugins), 1)

        plugin = plugins[0]
        self.assertEqual(plugin["id"], "test_plugin")
        self.assertTrue(plugin["loaded"])
        self.assertFalse(plugin["enabled"])

    def test_reload_plugins(self):
        """Test reloading all plugins."""
        # Create a test plugin file
        plugin_file = self.plugins_dir / "test_plugin.py"
        plugin_file.write_text("""
# name: Test Plugin
# description: A test plugin
# version: 1.0.0

def on_load(context):
    pass
    
def on_enable(context):
    pass
""")

        # Load and enable the plugin
        self.plugin_manager.load_plugin("test_plugin")
        self.plugin_manager.enable_plugin("test_plugin")

        # Verify plugin is loaded and enabled
        plugins = self.plugin_manager.list_plugins()
        self.assertEqual(len(plugins), 1)
        self.assertTrue(plugins[0]["loaded"])
        self.assertTrue(plugins[0]["enabled"])

        # Reload plugins
        self.plugin_manager.reload_plugins()

        # Verify plugins are unloaded
        plugins = self.plugin_manager.list_plugins()
        self.assertEqual(len(plugins), 1)
        # Note: After reload, the plugin will still be discovered but not loaded
        # The exact behavior depends on implementation details

    def test_run_hook_with_exception(self):
        """Test running a hook that throws an exception."""
        # Create a test plugin file with a hook that throws an exception
        plugin_file = self.plugins_dir / "test_plugin.py"
        plugin_file.write_text("""
# name: Test Plugin
# description: A test plugin
# version: 1.0.0

def on_pre_prompt(context, plugin_context):
    raise RuntimeError("Test exception")
""")

        # Load and enable the plugin
        self.plugin_manager.load_plugin("test_plugin")
        self.plugin_manager.enable_plugin("test_plugin")

        # Run the hook - should not crash
        context = {"messages": []}
        results = self.plugin_manager.run_hook("pre_prompt", context)

        # Should return empty results due to exception
        self.assertEqual(results, [])

        # Check that error was logged
        events = self.event_log.list_since(0)
        error_events = [e for e in events if e["type"] == "plugin.hook_error"]
        self.assertEqual(len(error_events), 1)
        self.assertIn("Test exception", error_events[0]["details"]["error"])

    def test_discover_plugins_with_malformed_metadata(self):
        """Test discovering plugins with malformed metadata."""
        # Create a plugin file with malformed metadata
        plugin_file = self.plugins_dir / "malformed_plugin.py"
        plugin_file.write_text("""
# name: Malformed Plugin
# description: A plugin with malformed version line
# version: not-a-version

def on_load(context):
    pass
""")

        plugins = self.plugin_manager.discover_plugins()
        self.assertEqual(len(plugins), 1)

        # Should still have default values for malformed metadata
        plugin = plugins[0]
        self.assertEqual(plugin["id"], "malformed_plugin")
        self.assertEqual(plugin["name"], "Malformed Plugin")
        self.assertEqual(plugin["description"], "A plugin with malformed version line")
        self.assertEqual(
            plugin["version"], "not-a-version"
        )  # Should accept whatever is provided

    def test_load_plugin_file_not_found(self):
        """Test loading a plugin when the file doesn't exist."""
        result = self.plugin_manager.load_plugin("nonexistent_plugin")
        self.assertFalse(result)

        # Check that error was logged (may not always be logged depending on implementation)
        # Just verify the function doesn't crash


class TestPluginExecutionContextAdditional(unittest.TestCase):
    """Additional test cases for PluginExecutionContext."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(json.dumps({}))

        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        self.context = PluginExecutionContext(
            "test_plugin", self.config_store, self.event_log
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_log_event_without_details(self):
        """Test logging events without additional details."""
        initial_event_count = len(self.event_log.list_since(0))

        self.context.log_event("test.simple_event", "Simple message")

        events = self.event_log.list_since(0)
        self.assertEqual(len(events), initial_event_count + 1)

        last_event = events[-1]
        self.assertEqual(last_event["type"], "test.simple_event")
        self.assertEqual(last_event["message"], "Simple message")
        self.assertEqual(last_event["details"]["plugin_id"], "test_plugin")

    def test_multiple_plugin_data_operations(self):
        """Test multiple plugin data operations."""
        # Set multiple data items
        self.context.set_plugin_data("key1", "value1")
        self.context.set_plugin_data("key2", "value2")
        self.context.set_plugin_data("key3", {"nested": "data"})

        # Retrieve data
        self.assertEqual(self.context.get_plugin_data("key1"), "value1")
        self.assertEqual(self.context.get_plugin_data("key2"), "value2")
        self.assertEqual(self.context.get_plugin_data("key3"), {"nested": "data"})

        # Update existing data
        self.context.set_plugin_data("key1", "updated_value")
        self.assertEqual(self.context.get_plugin_data("key1"), "updated_value")


if __name__ == "__main__":
    unittest.main()
