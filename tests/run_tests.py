#!/usr/bin/env python3
"""Test runner for MiniClaw."""
import sys
import unittest
from pathlib import Path

# Add the project root to the path so we can import miniclaw modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

if __name__ == '__main__':
    # Discover and run all tests
    loader = unittest.TestLoader()
    start_dir = str(Path(__file__).parent)
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with error code if tests failed
    sys.exit(0 if result.wasSuccessful() else 1)