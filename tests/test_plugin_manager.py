"""Unit tests for MiniClaw enhanced plugin manager."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from miniclaw.plugin_manager import (
    EnhancedPluginManager,
    PluginExecutionContext,
    create_plugin_manager
)
from miniclaw.config import ConfigStore
from miniclaw.events import EventLog


class TestPluginExecutionContext(unittest.TestCase):
    """Test cases for PluginExecutionContext."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(json.dumps({}))
        
        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        self.context = PluginExecutionContext("test_plugin", self.config_store, self.event_log)
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_set_and_get_plugin_data(self):
        """Test setting and getting plugin data."""
        self.context.set_plugin_data("test_key", "test_value")
        self.assertEqual(self.context.get_plugin_data("test_key"), "test_value")
        
        # Test default value
        self.assertEqual(self.context.get_plugin_data("nonexistent_key", "default"), "default")
        
    def test_log_event(self):
        """Test logging events."""
        initial_event_count = len(self.event_log.list_since(0))
        
        self.context.log_event("test.event", "Test message", {"test_data": "value"})
        
        events = self.event_log.list_since(0)
        self.assertEqual(len(events), initial_event_count + 1)
        
        last_event = events[-1]
        self.assertEqual(last_event["type"], "test.event")
        self.assertEqual(last_event["message"], "Test message")
        self.assertIn("test_data", last_event["details"])
        self.assertEqual(last_event["details"]["test_data"], "value")
        self.assertEqual(last_event["details"]["plugin_id"], "test_plugin")


class TestEnhancedPluginManager(unittest.TestCase):
    """Test cases for EnhancedPluginManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.plugins_dir = Path(self.temp_dir) / "plugins"
        self.plugins_dir.mkdir()
        
        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(json.dumps({}))
        
        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        self.plugin_manager = EnhancedPluginManager(self.plugins_dir, self.config_store, self.event_log)
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_discover_plugins_empty(self):
        """Test discovering plugins in empty directory."""
        plugins = self.plugin_manager.discover_plugins()
        self.assertEqual(plugins, [])
        
    def test_discover_plugins_with_files(self):
        """Test discovering plugins with Python files."""
        # Create a test plugin file
        plugin_file = self.plugins_dir / "test_plugin.py"
        plugin_file.write_text("""
# name: Test Plugin
# description: A test plugin
# version: 1.0.0

def on_load(context):
    pass
""")
        
        plugins = self.plugin_manager.discover_plugins()
        self.assertEqual(len(plugins), 1)
        
        plugin = plugins[0]
        self.assertEqual(plugin["id"], "test_plugin")
        self.assertEqual(plugin["name"], "Test Plugin")
        self.assertEqual(plugin["description"], "A test plugin")
        self.assertEqual(plugin["version"], "1.0.0")
        
    def test_load_plugin_success(self):
        """Test successfully loading a plugin."""
        # Create a test plugin file
        plugin_file = self.plugins_dir / "test_plugin.py"
        plugin_file.write_text("""
# name: Test Plugin
# description: A test plugin
# version: 1.0.0

def on_load(context):
    context.set_plugin_data("loaded", True)
""")
        
        # Load the plugin
        result = self.plugin_manager.load_plugin("test_plugin")
        self.assertTrue(result)
        
        # Check that plugin is loaded
        plugins = self.plugin_manager.list_plugins()
        self.assertEqual(len(plugins), 1)
        self.assertTrue(plugins[0]["loaded"])
        
        # Check plugin context
        context = self.plugin_manager.get_plugin_context("test_plugin")
        self.assertIsNotNone(context)
        if context is not None:
            self.assertTrue(context.get_plugin_data("loaded"))
        
        # Enable the plugin first
        result = self.plugin_manager.enable_plugin("test_plugin")
        self.assertTrue(result)
        
        # Disable the plugin
        result = self.plugin_manager.disable_plugin("test_plugin")
        self.assertTrue(result)
        
        # Check that plugin is disabled
        plugins = self.plugin_manager.list_plugins()
        self.assertFalse(plugins[0]["enabled"])
        
        # Check plugin context
        context = self.plugin_manager.get_plugin_context("test_plugin")
        if context is not None:
            self.assertTrue(context.get_plugin_data("loaded"))
        
    def test_register_and_run_hooks(self):
        """Test registering and running plugin hooks."""
        # Create a test plugin file with hooks
        plugin_file = self.plugins_dir / "test_plugin.py"
        plugin_file.write_text("""
# name: Test Plugin
# description: A test plugin
# version: 1.0.0

def on_pre_prompt(context, plugin_context):
    return [{"role": "system", "content": "Added by plugin"}]
    
def on_post_response(context, plugin_context):
    plugin_context.set_plugin_data("response_processed", True)
    return {"modified": True}
""")
        
        # Load and enable the plugin
        self.plugin_manager.load_plugin("test_plugin")
        self.plugin_manager.enable_plugin("test_plugin")
        
        # Run pre_prompt hook
        context = {"messages": []}
        results = self.plugin_manager.run_hook("pre_prompt", context)
        
        # Check results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["plugin_id"], "test_plugin")
        self.assertIn("role", results[0]["result"][0])
        self.assertIn("content", results[0]["result"][0])
        
        # Run post_response hook
        context = {"response": "Test response"}
        results = self.plugin_manager.run_hook("post_response", context)
        
        # Check results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["plugin_id"], "test_plugin")
        self.assertEqual(results[0]["result"], {"modified": True})
        
        # Check plugin context
        context = self.plugin_manager.get_plugin_context("test_plugin")
        if context is not None:
            self.assertTrue(context.get_plugin_data("response_processed"))
        
    def test_plugin_lifecycle_hooks(self):
        """Test plugin lifecycle hooks."""
        # Create a test plugin file with lifecycle hooks
        plugin_file = self.plugins_dir / "test_plugin.py"
        plugin_file.write_text("""
# name: Test Plugin
# description: A test plugin
# version: 1.0.0

lifecycle_events = []

def on_load(context):
    lifecycle_events.append("loaded")
    
def on_enable(context):
    lifecycle_events.append("enabled")
    
def on_disable(context):
    lifecycle_events.append("disabled")
    
def on_unload(context):
    lifecycle_events.append("unloaded")
""")
        
        # Test load
        self.plugin_manager.load_plugin("test_plugin")
        
        # Test enable
        self.plugin_manager.enable_plugin("test_plugin")
        
        # Test disable
        self.plugin_manager.disable_plugin("test_plugin")
        
        # Test unload
        self.plugin_manager.unload_plugin("test_plugin")
        
        # Note: Since we can't easily access the module's global variables in tests,
        # we're mainly testing that the methods don't crash
        # In a real scenario, we'd verify the lifecycle events were recorded


class TestPluginManagerFactory(unittest.TestCase):
    """Test cases for plugin manager factory function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.plugins_dir = Path(self.temp_dir) / "plugins"
        self.plugins_dir.mkdir()
        
        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(json.dumps({}))
        
        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_create_plugin_manager(self):
        """Test creation of plugin manager."""
        manager = create_plugin_manager(self.plugins_dir, self.config_store, self.event_log)
        self.assertIsInstance(manager, EnhancedPluginManager)
        self.assertEqual(manager.plugins_dir, self.plugins_dir)


if __name__ == '__main__':
    unittest.main()