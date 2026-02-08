#!/usr/bin/env python3
"""
Enhanced MiniClaw Demo Script

This script demonstrates the enhanced features of MiniClaw including:
- Enhanced security system
- Plugin system with hooks
- Setup wizard functionality
"""

import json
import tempfile
from pathlib import Path
import sys

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from miniclaw.security import create_security_managers
from miniclaw.plugin_manager import create_plugin_manager
from miniclaw.setup_wizard import SetupWizard
from miniclaw.config import ConfigStore
from miniclaw.events import EventLog


def demo_security_features():
    """Demonstrate security features."""
    print("=== Security Features Demo ===")
    
    # Create temporary directories for demo
    temp_dir = tempfile.mkdtemp()
    config_path = Path(temp_dir) / "config.json"
    config_path.write_text(json.dumps({
        "tools": {
            "working_directory": temp_dir
        }
    }))
    
    try:
        # Create security managers
        event_log = EventLog()
        config_store = ConfigStore(config_path, event_log)
        security = create_security_managers(config_store, event_log)
        
        sandbox = security["sandbox"]
        
        # Demonstrate command validation
        print("1. Command Validation:")
        safe_commands = ["ls -la", "echo hello", "pwd"]
        dangerous_commands = ["rm -rf /", "ls; rm -rf /", ":(){ :|:& };:"]
        
        for cmd in safe_commands:
            result = sandbox.validate_command(cmd)
            print(f"   '{cmd}' -> {'ALLOWED' if result else 'BLOCKED'}")
            
        for cmd in dangerous_commands:
            result = sandbox.validate_command(cmd)
            print(f"   '{cmd}' -> {'ALLOWED' if result else 'BLOCKED'}")
        
        # Demonstrate file path validation
        print("\n2. File Path Validation:")
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("test content")
        
        safe_paths = [str(test_file), str(Path(temp_dir) / "new_file.txt")]
        dangerous_paths = ["/etc/passwd", "/root/.ssh/id_rsa"]
        
        for path in safe_paths:
            result = sandbox.validate_file_path(path)
            print(f"   '{path}' -> {'ALLOWED' if result else 'BLOCKED'}")
            
        for path in dangerous_paths:
            result = sandbox.validate_file_path(path)
            print(f"   '{path}' -> {'ALLOWED' if result else 'BLOCKED'}")
            
        # Demonstrate input sanitization
        print("\n3. Input Sanitization:")
        test_inputs = [
            "Normal text input",
            "Text with null bytes: hello\x00world",
            "x" * 15000,  # Very long input
        ]
        
        for inp in test_inputs:
            sanitized = sandbox.sanitize_input(inp, max_length=100)
            status = "TRUNCATED" if len(inp) > 100 else "CLEAN"
            print(f"   Input length {len(inp)} -> {status} (output: {len(sanitized)} chars)")
            
    finally:
        # Clean up
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def demo_plugin_system():
    """Demonstrate plugin system features."""
    print("\n=== Plugin System Demo ===")
    
    # Create temporary directories for demo
    temp_dir = tempfile.mkdtemp()
    plugins_dir = Path(temp_dir) / "plugins"
    plugins_dir.mkdir()
    
    config_path = Path(temp_dir) / "config.json"
    config_path.write_text(json.dumps({}))
    
    try:
        # Create plugin manager
        event_log = EventLog()
        config_store = ConfigStore(config_path, event_log)
        plugin_manager = create_plugin_manager(plugins_dir, config_store, event_log)
        
        # Create a simple test plugin
        plugin_file = plugins_dir / "demo_plugin.py"
        plugin_file.write_text("""
# name: Demo Plugin
# description: A demonstration plugin
# version: 1.0.0

def on_load(context):
    context.log_event("demo.plugin.loaded", "Demo plugin loaded")
    context.set_plugin_data("load_time", __import__("time").time())

def on_enable(context):
    context.log_event("demo.plugin.enabled", "Demo plugin enabled")
    context.set_plugin_data("enable_count", context.get_plugin_data("enable_count", 0) + 1)

def on_pre_prompt(context, plugin_context):
    return [{"role": "system", "content": "[Demo Plugin] This message was added by the demo plugin"}]

def on_post_response(context, plugin_context):
    response = context.get("response", "")
    word_count = len(response.split())
    plugin_context.set_plugin_data("last_response_word_count", word_count)
    return {"word_count": word_count}
""")
        
        # Demonstrate plugin discovery
        print("1. Plugin Discovery:")
        plugins = plugin_manager.discover_plugins()
        print(f"   Found {len(plugins)} plugins")
        for plugin in plugins:
            print(f"   - {plugin['name']} (v{plugin['version']})")
        
        # Demonstrate plugin loading
        print("\n2. Plugin Loading:")
        if plugins:
            plugin_id = plugins[0]["id"]
            result = plugin_manager.load_plugin(plugin_id)
            print(f"   Loading '{plugin_id}' -> {'SUCCESS' if result else 'FAILED'}")
            
            # Demonstrate plugin enabling
            result = plugin_manager.enable_plugin(plugin_id)
            print(f"   Enabling '{plugin_id}' -> {'SUCCESS' if result else 'FAILED'}")
            
            # Demonstrate hook execution
            print("\n3. Hook Execution:")
            pre_prompt_result = plugin_manager.run_hook("pre_prompt", {"messages": []})
            print(f"   Pre-prompt hook result: {len(pre_prompt_result)} items")
            if pre_prompt_result:
                print(f"   Added message: {pre_prompt_result[0]['result'][0]['content']}")
                
            post_response_result = plugin_manager.run_hook("post_response", {"response": "This is a test response with several words"})
            print(f"   Post-response hook result: {len(post_response_result)} items")
            if post_response_result:
                print(f"   Word count: {post_response_result[0]['result']['word_count']}")
        
    finally:
        # Clean up
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def demo_setup_wizard():
    """Demonstrate setup wizard features."""
    print("\n=== Setup Wizard Demo ===")
    
    # Note: We won't actually run the interactive wizard in this demo
    # Instead, we'll show what it does
    
    print("The setup wizard provides:")
    print("1. Prerequisite checking (Python version, package managers)")
    print("2. Interactive provider configuration (Ollama, OpenAI, OpenRouter)")
    print("3. Telegram integration setup")
    print("4. Automatic workspace and file creation")
    print("5. Default configuration generation")
    
    print("\nExample provider configuration:")
    example_config = {
        "providers": {
            "default_provider_id": "ollama_default",
            "items": [
                {
                    "id": "ollama_default",
                    "name": "Ollama Default",
                    "type": "ollama",
                    "enabled": True,
                    "base_url": "http://localhost:11434",
                    "model": "qwen3",
                    "temperature": 0.2
                }
            ]
        }
    }
    print(json.dumps(example_config, indent=2))


def main():
    """Run all demos."""
    print("MiniClaw Enhanced Features Demo")
    print("=" * 50)
    
    demo_security_features()
    demo_plugin_system()
    demo_setup_wizard()
    
    print("\n" + "=" * 50)
    print("Demo completed successfully!")


if __name__ == "__main__":
    main()