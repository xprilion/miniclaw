"""
Example usage of the cricket scores plugin.

This example demonstrates how to use the cricket scores tool.
Note: This requires a properly configured MiniClaw environment.
"""

import sys
import os

# Add the miniclaw directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def example_usage():
    """Example of how to use the cricket scores tool."""
    print("Cricket Scores Plugin Example")
    print("=" * 30)
    
    # This is how you would use the tool in a real MiniClaw environment
    # The actual implementation requires the full MiniClaw framework
    
    print("""
In a real MiniClaw environment, you would use the tool like this:

{
  "tool": "get_cricket_scores",
  "arguments": {}
}

The tool will:
1. Try to fetch scores from Cricbuzz API
2. If that fails, try ESPN Cricinfo
3. If that fails, try web scraping
4. As a last resort, use web search

The response will include:
- Success status
- List of current scores
- Log of all attempts made
- Total number of attempts
- Human-readable message
    """)
    
    print("\nSample successful response:")
    print("""
{
  "success": true,
  "scores": [
    {
      "teams": "IND vs AUS",
      "score": "250/4 (45.2 Ov)",
      "status": "Live"
    },
    {
      "teams": "ENG vs NZ",
      "score": "320/5 (50 Ov) vs 275/8 (50 Ov)",
      "status": "Completed"
    }
  ],
  "attempt_log": [
    "Attempted Cricbuzz API",
    "Found scores from Cricbuzz"
  ],
  "total_attempts": 1,
  "message": "Successfully retrieved 2 cricket score(s)"
}
    """)
    
    print("\nSample failure response:")
    print("""
{
  "success": false,
  "scores": [],
  "attempt_log": [
    "Attempted Cricbuzz API",
    "Attempted ESPN Cricinfo",
    "Web scraping failed: Timeout",
    "Used web search as fallback"
  ],
  "total_attempts": 4,
  "message": "Failed to retrieve cricket scores after all attempts",
  "error": "No scores found from any source"
}
    """)

if __name__ == "__main__":
    example_usage()