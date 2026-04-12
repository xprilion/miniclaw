#!/usr/bin/env python3
"""
Test script for Brave Search integration in MiniClaw.
"""

import sys
import os

# Add the miniclaw package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from miniclaw.tools.brave_search import BraveSearchClient

def test_brave_search():
    """Test the Brave Search client with a simple query."""
    api_key = "BSAW9orqbdUdha3-8bXvUK_VPOI3r2N"
    
    client = BraveSearchClient(api_key)
    
    try:
        print("Testing Brave Search with query: 'latest AI breakthroughs 2026'")
        results = client.search("latest AI breakthroughs 2026", count=3)
        formatted = client.format_results(results)
        
        print(f"Found {len(formatted)} results:")
        for i, result in enumerate(formatted, 1):
            print(f"{i}. {result['title']}")
            print(f"   URL: {result['url']}")
            print(f"   Snippet: {result['snippet'][:100]}...")
            print()
            
    except Exception as e:
        print(f"Error: {e}")
        return False
        
    return True

if __name__ == "__main__":
    success = test_brave_search()
    sys.exit(0 if success else 1)