#!/usr/bin/env python3
"""
Test the Brave Search tool integration in MiniClaw.
"""

import sys
import os
import json

# Add the miniclaw package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

def test_brave_search_tool():
    """Test the Brave Search tool."""
    try:
        # Import the necessary modules
        from miniclaw.core.config import ConfigStore
        from miniclaw.core.events import EventLog
        from miniclaw.services.mcp import MCPServerManager
        from miniclaw.tools.tools import ToolRunner
        
        # Create minimal required objects
        config_store = ConfigStore("/home/xprilion/.miniclaw/miniclaw_config.json")
        event_log = EventLog(700)  # max_events from config
        mcp_manager = MCPServerManager(config_store, event_log)
        
        # Create tool runner
        tool_runner = ToolRunner(config_store, event_log, mcp_manager)
        
        # List all available tools to verify brave_search is there
        tools = tool_runner.catalog()
        tool_names = [tool['name'] for tool in tools]
        print('Available tools:', tool_names)
        
        # Check if brave_search is available
        if 'brave_search' in tool_names:
            print('✓ Brave Search tool is available')
            
            # Test the brave_search tool
            print("Testing Brave Search tool...")
            result = tool_runner.run(
                "brave_search",
                {
                    "query": "latest AI research papers 2026",
                    "count": 3
                }
            )
            
            print("Brave Search tool result:")
            print(json.dumps(result, indent=2))
        else:
            print('✗ Brave Search tool is NOT available')
            return False
        
        return True
        
    except Exception as e:
        print(f"Error testing Brave Search tool: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_brave_search_tool()
    sys.exit(0 if success else 1)