#!/usr/bin/env python3
"""Test runner for MiniClaw."""

import sys
import unittest
from pathlib import Path

# Add the project root to the path so we can import miniclaw modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_tests_with_coverage():
    """Run tests with coverage measurement."""
    try:
        import coverage

        cov = coverage.Coverage()
        cov.start()
    except ImportError:
        print("Coverage module not found. Install it with 'pip install coverage'")
        return False

    # Discover and run all tests
    loader = unittest.TestLoader()
    start_dir = str(Path(__file__).parent)
    suite = loader.discover(start_dir, pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Stop coverage and generate report
    cov.stop()
    cov.save()
    print("\nCoverage Report:")
    cov.report()
    print("\nHTML coverage report generated in htmlcov/")
    cov.html_report()

    return result.wasSuccessful()


def run_tests():
    """Run tests without coverage measurement."""
    # Discover and run all tests
    loader = unittest.TestLoader()
    start_dir = str(Path(__file__).parent)
    suite = loader.discover(start_dir, pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    # Check if we want to run with coverage
    use_coverage = "--coverage" in sys.argv

    if use_coverage:
        success = run_tests_with_coverage()
    else:
        success = run_tests()

    # Exit with error code if tests failed
    sys.exit(0 if success else 1)
