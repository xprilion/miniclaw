"""Test CLI consistency and styling across commands."""
import unittest
from pathlib import Path


class TestCLIConsistency(unittest.TestCase):
    """Test CLI consistency and styling."""

    def test_cli_functions_updated(self):
        """Test that CLI functions have been updated with styling."""
        cli_file = Path(__file__).parent.parent / "miniclaw" / "cli" / "cli.py"
        content = cli_file.read_text()
        
        # Should reference the new styling
        self.assertIn("CLIStyle", content)
        self.assertIn("cli_utils", content)
        
        # Should have updated key commands
        self.assertIn("style.success", content)
        self.assertIn("style.error", content)
        self.assertIn("style.warning", content)
        self.assertIn("style.info", content)
        self.assertIn("style.header", content)

    def test_cli_functions_exist(self):
        """Test that updated CLI functions exist and are callable."""
        from miniclaw.cli.cli import run_install, run_doctor, run_update, run_uninstall
        
        # Test that functions exist (we can't easily test execution without mocks)
        self.assertTrue(callable(run_install))
        self.assertTrue(callable(run_doctor))
        self.assertTrue(callable(run_update))
        self.assertTrue(callable(run_uninstall))

    def test_enhanced_setup_wizard_uses_styling(self):
        """Test that enhanced setup wizard uses the new styling."""
        setup_file = Path(__file__).parent.parent / "miniclaw" / "setup" / "enhanced_setup_wizard.py"
        content = setup_file.read_text()
        
        # Should reference CLI utilities
        self.assertIn("cli_utils", content)
        self.assertIn("CLIExperience", content)
        self.assertIn("CLIStyle", content)

    def test_consistent_error_handling(self):
        """Test that CLI has consistent error handling patterns."""
        cli_file = Path(__file__).parent.parent / "miniclaw" / "cli" / "cli.py"
        content = cli_file.read_text()
        
        # Should use style.error for error messages
        self.assertIn("style.error", content)
        
        # Should have consistent return codes
        self.assertIn("return 0", content)
        self.assertIn("return 1", content)


if __name__ == "__main__":
    unittest.main()