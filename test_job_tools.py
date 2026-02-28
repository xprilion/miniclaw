#!/usr/bin/env python3
"""
Test the job management tools integration in MiniClaw.
"""

import sys
import os
import json

# Add the miniclaw package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

def test_job_tools_available():
    """Test that job management tools are available."""
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
        
        # List all available tools to verify job tools are there
        tools = tool_runner.catalog()
        tool_names = [tool['name'] for tool in tools]
        print('Available tools:', tool_names)
        
        # Check if job management tools are available
        job_tools = ['jobs_create', 'jobs_list', 'jobs_delete', 'jobs_run']
        available_job_tools = [tool for tool in job_tools if tool in tool_names]
        
        if available_job_tools:
            print('✓ Job management tools available:', available_job_tools)
            return True
        else:
            print('✗ Job management tools NOT available')
            return False
        
    except Exception as e:
        print(f"Error testing job tools: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_job_tools_available()
    sys.exit(0 if success else 1)