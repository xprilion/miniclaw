#!/usr/bin/env python3
"""Simple test for cricket scores plugin without full framework dependencies."""

import sys
import os
import re

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

def test_score_extraction_logic():
    """Test the score extraction logic independently."""
    # Test HTML content with scores
    html_content = """
    <div class="match">
        <h3>IND vs AUS</h3>
        <span>IND 250/4 (45.2 Ov)</span>
        <span>AUS 180/7 (35.0 Ov)</span>
    </div>
    """
    
    # Test the extraction logic directly
    scores = []
    
    # Pattern for live score summaries (generic pattern that works for many sites)
    score_patterns = [
        r'([A-Z]{2,4})\s+([0-9]+/[0-9]+)\s*\(?([0-9.]*)\s*ov?e?r?s?\)?\s*(?:&\s*)?([A-Z]{2,4})?\s*([0-9]+/[0-9]+)?\s*\(?([0-9.]*)\s*ov?e?r?s?\)?',
        r'([A-Z]{2,4})\s+vs\s+([A-Z]{2,4}).*?([0-9]+/[0-9]+).*?([0-9.]+) ov',
        r'<div[^>]*class="[^"]*score[^"]*"[^>]*>(.*?)</div>',
    ]
    
    for pattern in score_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
        for match in matches:
            try:
                if isinstance(match, tuple) and len(match) >= 2:
                    score_info = {
                        "teams": f"{match[0]} vs {match[3] if len(match) > 3 and match[3] else 'Opponent'}",
                        "score": f"{match[1]} {f'({match[2]} ov)' if len(match) > 2 and match[2] else ''}",
                        "status": "Live"
                    }
                    scores.append(score_info)
            except Exception as e:
                print(f"Failed to parse score match: {e}")
                continue
    
    print("Extracted scores:", scores)
    
    # Simple validation
    if len(scores) > 0:
        print("✓ Score extraction test passed")
        return True
    else:
        print("✗ Score extraction test failed")
        return False

def main():
    """Run simple tests."""
    print("Running simple cricket scores plugin tests...")
    print("=" * 50)
    
    tests = [
        test_regex_patterns,
        test_score_extraction_logic
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