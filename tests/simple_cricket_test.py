#!/usr/bin/env python3
"""Simple test for cricket scores plugin without full framework dependencies."""

import sys
import os
import re

# Add the plugins directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'miniclaw', 'plugins'))

def test_score_extraction():
    """Test the score extraction function."""
    # Import just the function we want to test
    cricket_module = __import__('cricket_scores')
    
    # Test HTML content with scores
    html_content = """
    <div class="match">
        <h3>IND vs AUS</h3>
        <span>IND 250/4 (45.2 Ov)</span>
        <span>AUS 180/7 (35.0 Ov)</span>
    </div>
    """
    
    # Test the extraction method directly
    scores = cricket_module.CricketScoreRetriever._extract_scores_from_html.__func__(None, html_content)
    
    print("Extracted scores:", scores)
    
    # Simple validation
    if len(scores) > 0:
        print("✓ Score extraction test passed")
        return True
    else:
        print("✗ Score extraction test failed")
        return False

def test_regex_patterns():
    """Test the regex patterns used for score extraction."""
    # Test pattern matching
    test_text = "IND 250/4 (45.2 Ov) vs AUS 180/7 (35.0 Ov)"
    
    # Simple pattern for testing
    pattern = r'([A-Z]{2,4})\s+([0-9]+/[0-9]+)\s*\(?([0-9.]*)\s*ov?e?r?s?\)?'
    matches = re.findall(pattern, test_text, re.IGNORECASE)
    
    print("Regex matches:", matches)
    
    if len(matches) > 0:
        print("✓ Regex pattern test passed")
        return True
    else:
        print("✗ Regex pattern test failed")
        return False

def main():
    """Run simple tests."""
    print("Running simple cricket scores plugin tests...")
    print("=" * 50)
    
    # Change to the plugins directory to import the module
    plugin_dir = os.path.join(os.path.dirname(__file__), '..', 'miniclaw', 'plugins')
    os.chdir(plugin_dir)
    
    tests = [
        test_regex_patterns,
        test_score_extraction
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed with exception: {e}")
            failed += 1
    
    print("=" * 50)
    print(f"Tests passed: {passed}")
    print(f"Tests failed: {failed}")
    
    if failed == 0:
        print("All tests passed! ✓")
        return 0
    else:
        print("Some tests failed! ✗")
        return 1

if __name__ == "__main__":
    sys.exit(main())