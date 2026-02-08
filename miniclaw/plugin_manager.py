"""Enhanced plugin manager for MiniClaw with improved extensibility and lifecycle management."""
from __future__ import annotations

import importlib.util
import inspect
import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from .config import ConfigStore
from .events import EventLog
from .util import LOGGER


class PluginLifecycleHook:
    """Base class for plugin lifecycle hooks."""
    
    def on_load(self, plugin_context: Dict[str, Any]) -> None:
        """Called when plugin is loaded."""
        pass
        
    def on_unload(self, plugin_context: Dict[str, Any]) -> None:
        """Called when plugin is unloaded."""
        pass
        
    def on_enable(self, plugin_context: Dict[str, Any]) -> None:
        """Called when plugin is enabled."""
        pass
        
    def on_disable(self, plugin_context: Dict[str, Any]) -> None:
        """Called when plugin is disabled."""
        pass


class PluginExecutionContext:
    """Context provided to plugins during execution."""
    
    def __init__(self, plugin_id: str, config_store: ConfigStore, event_log: EventLog) -> None:
        self.plugin_id = plugin_id
        self.config_store = config_store
        self.event_log = event_log
        self._plugin_data: Dict[str, Any] = {}
        
    def get_plugin_data(self, key: str, default: Any = None) -> Any:
        """Get plugin-specific data."""
        return self._plugin_data.get(key, default)
        
    def set_plugin_data(self, key: str, value: Any) -> None:
        """Set plugin-specific data."""
        self._plugin_data[key] = value
        
    def log_event(self, event_type: str, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Log a plugin-specific event."""
        self.event_log.add(
            event_type,
            message,
            {**(data or {}), "plugin_id": self.plugin_id}
        )


class EnhancedPluginManager:
    """Enhanced plugin manager with improved lifecycle management and extensibility."""
    
    def __init__(self, plugins_dir: Path, config_store: ConfigStore, event_log: EventLog) -> None:
        self.plugins_dir = plugins_dir
        self.config_store = config_store
        self.event_log = event_log
        self.plugins: Dict[str, Dict[str, Any]] = {}
        self.enabled_plugins: Set[str] = set()
        self.hooks: Dict[str, List[Tuple[str, Callable]]] = {
            "pre_prompt": [],
            "post_response": [],
            "on_message": [],
            "on_tool_call": [],
            "on_model_response": [],
        }
        self.plugin_contexts: Dict[str, PluginExecutionContext] = {}
        
    def discover_plugins(self) -> List[Dict[str, Any]]:
        """Discover available plugins in the plugins directory."""
        plugins = []
        
        if not self.plugins_dir.exists():
            return plugins
            
        for item in self.plugins_dir.iterdir():
            if item.is_file() and item.suffix == ".py" and item.name != "__init__.py":
                plugin_info = self._load_plugin_metadata(item)
                if plugin_info:
                    plugins.append(plugin_info)
            elif item.is_dir() and (item / "__init__.py").exists():
                plugin_info = self._load_plugin_metadata(item / "__init__.py")
                if plugin_info:
                    plugins.append(plugin_info)
                    
        return plugins
        
    def _load_plugin_metadata(self, plugin_path: Path) -> Optional[Dict[str, Any]]:
        """Load plugin metadata from a Python file."""
        try:
            # Read the file to extract metadata without importing
            content = plugin_path.read_text(encoding="utf-8")
            
            # Extract basic metadata from comments or docstrings
            plugin_id = plugin_path.stem
            name = plugin_id.replace("_", " ").title()
            description = f"Plugin {plugin_id}"
            version = "1.0.0"
            
            # Look for metadata in comments
            for line in content.split("\n")[:20]:  # Check first 20 lines
                line = line.strip()
                if line.startswith("# name:"):
                    name = line[7:].strip()
                elif line.startswith("# description:"):
                    description = line[13:].strip()
                elif line.startswith("# version:"):
                    version = line[10:].strip()
                    
            return {
                "id": plugin_id,
                "name": name,
                "description": description,
                "version": version,
                "path": str(plugin_path),
                "enabled": False,
                "loaded": False,
            }
        except Exception as e:
            LOGGER.warning(f"Failed to load metadata for plugin {plugin_path}: {e}")
            return None
            
    def load_plugin(self, plugin_id: str) -> bool:
        """Load a specific plugin by ID."""
        try:
            # Find the plugin
            discovered = self.discover_plugins()
            plugin_info = next((p for p in discovered if p["id"] == plugin_id), None)
            
            if not plugin_info:
                LOGGER.error(f"Plugin {plugin_id} not found")
                return False
                
            # Load the module
            spec = importlib.util.spec_from_file_location(plugin_id, plugin_info["path"])
            if not spec or not spec.loader:
                LOGGER.error(f"Failed to create spec for plugin {plugin_id}")
                return False
                
            module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_id] = module
            spec.loader.exec_module(module)
            
            # Create plugin context
            context = PluginExecutionContext(plugin_id, self.config_store, self.event_log)
            self.plugin_contexts[plugin_id] = context
            
            # Store plugin info
            plugin_info["loaded"] = True
            plugin_info["_module"] = module
            plugin_info["_context"] = context
            self.plugins[plugin_id] = plugin_info
            
            # Register hooks
            self._register_plugin_hooks(plugin_id, module)
            
            # Call onLoad if it exists
            if hasattr(module, "on_load"):
                try:
                    module.on_load(context)
                except Exception as e:
                    LOGGER.error(f"Error in onLoad for plugin {plugin_id}: {e}")
                    
            self.event_log.add(
                "plugin.loaded",
                f"Plugin {plugin_id} loaded successfully",
                {"plugin_id": plugin_id}
            )
            
            return True
            
        except Exception as e:
            LOGGER.error(f"Failed to load plugin {plugin_id}: {e}")
            self.event_log.add(
                "plugin.load_error",
                f"Failed to load plugin {plugin_id}",
                {"plugin_id": plugin_id, "error": str(e), "traceback": traceback.format_exc()}
            )
            return False
            
    def unload_plugin(self, plugin_id: str) -> bool:
        """Unload a specific plugin by ID."""
        if plugin_id not in self.plugins:
            return False
            
        try:
            plugin_info = self.plugins[plugin_id]
            
            # Call onUnload if it exists
            module = plugin_info.get("_module")
            if module and hasattr(module, "on_unload"):
                try:
                    context = self.plugin_contexts.get(plugin_id)
                    module.on_unload(context)
                except Exception as e:
                    LOGGER.error(f"Error in onUnload for plugin {plugin_id}: {e}")
                    
            # Unregister hooks
            self._unregister_plugin_hooks(plugin_id)
            
            # Remove from sys.modules
            if plugin_id in sys.modules:
                del sys.modules[plugin_id]
                
            # Remove plugin data
            if plugin_id in self.plugin_contexts:
                del self.plugin_contexts[plugin_id]
                
            # Mark as unloaded
            plugin_info["loaded"] = False
            plugin_info["enabled"] = False
            if plugin_id in self.enabled_plugins:
                self.enabled_plugins.remove(plugin_id)
                
            self.event_log.add(
                "plugin.unloaded",
                f"Plugin {plugin_id} unloaded successfully",
                {"plugin_id": plugin_id}
            )
            
            return True
            
        except Exception as e:
            LOGGER.error(f"Failed to unload plugin {plugin_id}: {e}")
            self.event_log.add(
                "plugin.unload_error",
                f"Failed to unload plugin {plugin_id}",
                {"plugin_id": plugin_id, "error": str(e)}
            )
            return False
            
    def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a loaded plugin."""
        if plugin_id not in self.plugins:
            # Try to load it first
            if not self.load_plugin(plugin_id):
                return False
                
        plugin_info = self.plugins[plugin_id]
        if not plugin_info["loaded"]:
            return False
            
        try:
            # Call onEnable if it exists
            module = plugin_info.get("_module")
            if module and hasattr(module, "on_enable"):
                try:
                    context = self.plugin_contexts.get(plugin_id)
                    module.on_enable(context)
                except Exception as e:
                    LOGGER.error(f"Error in onEnable for plugin {plugin_id}: {e}")
                    
            plugin_info["enabled"] = True
            self.enabled_plugins.add(plugin_id)
            
            self.event_log.add(
                "plugin.enabled",
                f"Plugin {plugin_id} enabled successfully",
                {"plugin_id": plugin_id}
            )
            
            return True
            
        except Exception as e:
            LOGGER.error(f"Failed to enable plugin {plugin_id}: {e}")
            self.event_log.add(
                "plugin.enable_error",
                f"Failed to enable plugin {plugin_id}",
                {"plugin_id": plugin_id, "error": str(e)}
            )
            return False
            
    def disable_plugin(self, plugin_id: str) -> bool:
        """Disable an enabled plugin."""
        if plugin_id not in self.plugins or plugin_id not in self.enabled_plugins:
            return False
            
        try:
            plugin_info = self.plugins[plugin_id]
            
            # Call onDisable if it exists
            module = plugin_info.get("_module")
            if module and hasattr(module, "on_disable"):
                try:
                    context = self.plugin_contexts.get(plugin_id)
                    module.on_disable(context)
                except Exception as e:
                    LOGGER.error(f"Error in onDisable for plugin {plugin_id}: {e}")
                    
            plugin_info["enabled"] = False
            self.enabled_plugins.remove(plugin_id)
            
            self.event_log.add(
                "plugin.disabled",
                f"Plugin {plugin_id} disabled successfully",
                {"plugin_id": plugin_id}
            )
            
            return True
            
        except Exception as e:
            LOGGER.error(f"Failed to disable plugin {plugin_id}: {e}")
            self.event_log.add(
                "plugin.disable_error",
                f"Failed to disable plugin {plugin_id}",
                {"plugin_id": plugin_id, "error": str(e)}
            )
            return False
            
    def _register_plugin_hooks(self, plugin_id: str, module: Any) -> None:
        """Register plugin hooks from the module."""
        # Register lifecycle hooks
        for hook_name in self.hooks.keys():
            hook_func_name = f"on_{hook_name}"
            if hasattr(module, hook_func_name):
                hook_func = getattr(module, hook_func_name)
                if callable(hook_func):
                    self.hooks[hook_name].append((plugin_id, hook_func))
                    
    def _unregister_plugin_hooks(self, plugin_id: str) -> None:
        """Unregister plugin hooks."""
        for hook_list in self.hooks.values():
            hook_list[:] = [hook for hook in hook_list if hook[0] != plugin_id]
            
    def run_hook(self, hook_name: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run a specific hook with context."""
        if hook_name not in self.hooks:
            return []
            
        results = []
        for plugin_id, hook_func in self.hooks[hook_name]:
            if plugin_id in self.enabled_plugins:
                try:
                    plugin_context = self.plugin_contexts.get(plugin_id)
                    result = hook_func(context, plugin_context) if plugin_context else hook_func(context)
                    if result is not None:
                        results.append({
                            "plugin_id": plugin_id,
                            "result": result
                        })
                except Exception as e:
                    LOGGER.error(f"Error in {hook_name} hook for plugin {plugin_id}: {e}")
                    self.event_log.add(
                        "plugin.hook_error",
                        f"Error in {hook_name} hook for plugin {plugin_id}",
                        {"plugin_id": plugin_id, "hook": hook_name, "error": str(e)}
                    )
                    
        return results
        
    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all plugins with their status."""
        discovered = self.discover_plugins()
        plugin_list = []
        
        for plugin_info in discovered:
            plugin_id = plugin_info["id"]
            loaded_info = self.plugins.get(plugin_id, {})
            
            plugin_list.append({
                "id": plugin_id,
                "name": plugin_info["name"],
                "description": plugin_info["description"],
                "version": plugin_info["version"],
                "loaded": loaded_info.get("loaded", False),
                "enabled": plugin_id in self.enabled_plugins,
                "path": plugin_info["path"],
            })
            
        # Include loaded plugins that might not be discovered
        for plugin_id, plugin_info in self.plugins.items():
            if not any(p["id"] == plugin_id for p in plugin_list):
                plugin_list.append({
                    "id": plugin_id,
                    "name": plugin_id.replace("_", " ").title(),
                    "description": "Loaded plugin",
                    "version": "unknown",
                    "loaded": plugin_info.get("loaded", False),
                    "enabled": plugin_id in self.enabled_plugins,
                    "path": plugin_info.get("path", "unknown"),
                })
                
        return plugin_list
        
    def reload_plugins(self) -> None:
        """Reload all plugins."""
        # Disable all plugins first
        for plugin_id in list(self.enabled_plugins):
            self.disable_plugin(plugin_id)
            
        # Unload all plugins
        for plugin_id in list(self.plugins.keys()):
            self.unload_plugin(plugin_id)
            
        # Clear hooks
        for hook_list in self.hooks.values():
            hook_list.clear()
            
        self.event_log.add("plugin.manager_reloaded", "Plugin manager reloaded")
        
    def get_plugin_context(self, plugin_id: str) -> Optional[PluginExecutionContext]:
        """Get the execution context for a plugin."""
        return self.plugin_contexts.get(plugin_id)


def create_plugin_manager(plugins_dir: Path, config_store: ConfigStore, event_log: EventLog) -> EnhancedPluginManager:
    """Factory function to create an enhanced plugin manager."""
    return EnhancedPluginManager(plugins_dir, config_store, event_log)