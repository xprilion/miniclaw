"""Test cricket scores plugin."""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the miniclaw directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'miniclaw'))

from miniclaw.plugins.cricket_scores import CricketScoreRetriever


class MockToolRunner:
    """Mock tool runner for testing."""
    
    def run(self, tool_name, arguments):
        """Mock run method."""
        if tool_name == "fetch_url":
            # Return mock data for Cricbuzz
            if "cricbuzz" in arguments.get("url", ""):
                return {
                    "ok": True,
                    "result": {
                        "body": """
                        <div class="cb-mtch-lst-itm">
                            <div class="cb-lv-scr-well">
                                <div class="cb-lv-scr-well-left">
                                    <h3>IND vs AUS</h3>
                                    <div class="cb-lv-scr-well-info">
                                        <span class="cb-lv-scr-well-info-team">IND</span>
                                        <span class="cb-lv-scr-well-info-score">250/4 (45.2 Ov)</span>
                                    </div>
                                    <div class="cb-lv-scr-well-info">
                                        <span class="cb-lv-scr-well-info-team">AUS</span>
                                        <span class="cb-lv-scr-well-info-score">180/7 (35.0 Ov)</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        """
                    }
                }
            # Return mock data for ESPN Cricinfo
            elif "espncricinfo" in arguments.get("url", ""):
                return {
                    "ok": True,
                    "result": {
                        "body": """
                        <div class="scorecard-container">
                            <div class="match-header">
                                <h2>England vs New Zealand</h2>
                                <div class="scorecard-table">
                                    <div class="scorecard-item">
                                        <span>ENG</span>
                                        <span>320/5 (50 Ov)</span>
                                    </div>
                                    <div class="scorecard-item">
                                        <span>NZ</span>
                                        <span>275/8 (50 Ov)</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        """
                    }
                }
            # Return mock data for Google search
            elif "google.com" in arguments.get("url", ""):
                return {
                    "ok": True,
                    "result": {
                        "text": "Live Cricket Scores - IND 250/4 (45.2 Ov) vs AUS 180/7 (35.0 Ov)"
                    }
                }
        elif tool_name == "brave_search":
            return {
                "ok": True,
                "result": {
                    "results": [
                        {
                            "title": "Live Cricket Score: India vs Australia",
                            "description": "IND 250/4 (45.2 Ov) vs AUS 180/7 (35.0 Ov) - Live match",
                            "url": "https://example.com/cricket/live"
                        }
                    ]
                }
            }
        elif tool_name == "browser_extract":
            return {
                "ok": True,
                "result": {
                    "text": "Live Cricket Scores - IND 250/4 (45.2 Ov) vs AUS 180/7 (35.0 Ov)"
                }
            }
        
        # Default response for other tools
        return {"ok": False, "error": "Tool not implemented in mock"}


class TestCricketScoreRetriever(unittest.TestCase):
    """Test CricketScoreRetriever class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_tool_runner = MockToolRunner()
        self.retriever = CricketScoreRetriever(self.mock_tool_runner)

    def test_initialization(self):
        """Test that the retriever initializes correctly."""
        self.assertIsInstance(self.retriever, CricketScoreRetriever)
        self.assertEqual(self.retriever.max_retries, 3)
        self.assertEqual(self.retriever.retry_delay, 2)

    @patch('time.sleep', return_value=None)  # Mock sleep to speed up tests
    def test_run_tool_with_retry_success(self, mock_sleep):
        """Test successful tool execution with retry."""
        result = self.retriever._run_tool_with_retry("fetch_url", {"url": "https://www.cricbuzz.com"})
        self.assertTrue(result["ok"])
        self.assertIn("body", result["result"])

    @patch('time.sleep', return_value=None)  # Mock sleep to speed up tests
    def test_run_tool_with_retry_failure(self, mock_sleep):
        """Test tool execution failure after retries."""
        with self.assertRaises(Exception) as context:
            self.retriever._run_tool_with_retry("nonexistent_tool", {})
        
        self.assertIn("Failed to execute nonexistent_tool", str(context.exception))

    def test_extract_scores_from_html(self):
        """Test extracting scores from HTML content."""
        html_content = """
        <div class="match">
            <h3>IND vs AUS</h3>
            <span>IND 250/4 (45.2 Ov)</span>
            <span>AUS 180/7 (35.0 Ov)</span>
        </div>
        """
        scores = self.retriever._extract_scores_from_html(html_content)
        self.assertGreater(len(scores), 0)

    @patch('time.sleep', return_value=None)  # Mock sleep to speed up tests
    def test_get_cricbuzz_scores(self, mock_sleep):
        """Test getting scores from Cricbuzz."""
        scores = self.retriever._get_cricbuzz_scores()
        # In our mock, this should return scores
        self.assertGreater(len(scores), 0)

    @patch('time.sleep', return_value=None)  # Mock sleep to speed up tests
    def test_get_espncricinfo_scores(self, mock_sleep):
        """Test getting scores from ESPN Cricinfo."""
        scores = self.retriever._get_espncricinfo_scores()
        # In our mock, this should return scores
        self.assertGreater(len(scores), 0)

    @patch('time.sleep', return_value=None)  # Mock sleep to speed up tests
    def test_get_cricket_scores_via_search(self, mock_sleep):
        """Test getting scores via web search."""
        scores = self.retriever._get_cricket_scores_via_search()
        # In our mock, this should return scores
        self.assertGreater(len(scores), 0)

    @patch('time.sleep', return_value=None)  # Mock sleep to speed up tests
    def test_get_cricket_scores_full_flow(self, mock_sleep):
        """Test the full cricket score retrieval flow."""
        result = self.retriever.get_cricket_scores()
        
        # Check that the result has the expected structure
        self.assertIn("success", result)
        self.assertIn("scores", result)
        self.assertIn("attempt_log", result)
        self.assertIn("total_attempts", result)
        self.assertIn("message", result)
        
        # Should be successful with our mock data
        self.assertTrue(result["success"])
        self.assertGreater(len(result["scores"]), 0)


if __name__ == '__main__':
    unittest.main()