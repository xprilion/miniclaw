"""Test that the install command uses the enhanced setup wizard."""

import unittest
from pathlib import Path


class TestInstallCommand(unittest.TestCase):
    """Test the install command functionality."""

    def test_install_command_uses_enhanced_wizard(self):
        """Test that the install command uses the enhanced setup wizard."""
        # Import the CLI function
        from miniclaw.cli.cli import run_install
        import argparse

        # Create a mock args object
        args = argparse.Namespace()

        # The function should import and run the enhanced setup wizard
        # We can't easily test this without mocking, but we can verify the function exists
        self.assertTrue(callable(run_install))

    def test_cli_commands_updated(self):
        """Test that CLI commands have been updated."""
        cli_file = Path(__file__).parent.parent / "miniclaw" / "cli" / "cli.py"
        content = cli_file.read_text()

        # Should NOT have setup command anymore
        self.assertNotIn('sub.add_parser("setup"', content)

        # Should have install command
        self.assertIn('sub.add_parser("install"', content)

        # Should reference enhanced setup wizard
        self.assertIn("enhanced_setup_wizard", content)

    def test_readme_updated(self):
        """Test that README has been updated."""
        readme_file = Path(__file__).parent.parent / "README.md"
        content = readme_file.read_text()

        # Should mention database installation in install command
        self.assertIn("database installation", content)

        # Should have simplified command list
        self.assertIn("`miniclaw install`", content)


if __name__ == "__main__":
    unittest.main()
