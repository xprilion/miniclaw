"""Test CLI styling and unified experience."""
import unittest
from pathlib import Path


class TestCLIStyling(unittest.TestCase):
    """Test CLI styling functionality."""

    def test_cli_utils_import(self):
        """Test that CLI utilities can be imported."""
        try:
            from miniclaw.cli_utils import CLIExperience, CLIStyle, CLIColors
            self.assertTrue(True)
        except ImportError:
            self.fail("Failed to import CLI utilities")

    def test_cli_utils_functionality(self):
        """Test that CLI utilities have expected functionality."""
        from miniclaw.cli_utils import CLIExperience, CLIStyle
        
        # Test CLIStyle methods
        style = CLIStyle()
        self.assertIsInstance(style.success("test"), str)
        self.assertIsInstance(style.error("test"), str)
        self.assertIsInstance(style.warning("test"), str)
        self.assertIsInstance(style.info("test"), str)
        self.assertIsInstance(style.header("test"), str)
        self.assertIsInstance(style.step("test", step_num=1, total_steps=5), str)
        
        # Test CLIExperience
        cli = CLIExperience("TestApp")
        self.assertEqual(cli.app_name, "TestApp")

    def test_cli_utils_file_exists(self):
        """Test that CLI utilities file exists."""
        utils_file = Path(__file__).parent.parent / "miniclaw" / "cli_utils.py"
        self.assertTrue(utils_file.exists(), f"Expected {utils_file} to exist")

    def test_cli_updated_commands(self):
        """Test that CLI commands have been updated with styling."""
        cli_file = Path(__file__).parent.parent / "miniclaw_cli.py"
        content = cli_file.read_text()
        
        # Should reference the new styling
        self.assertIn("cli_utils", content)
        self.assertIn("CLIStyle", content)
        self.assertIn("style.success", content)
        self.assertIn("style.error", content)


if __name__ == "__main__":
    unittest.main()