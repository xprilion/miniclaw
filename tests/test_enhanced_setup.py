"""Test the enhanced setup wizard."""
import unittest
from pathlib import Path


class TestEnhancedSetupWizard(unittest.TestCase):
    """Test the enhanced setup wizard functionality."""

    def test_enhanced_setup_wizard_import(self):
        """Test that the enhanced setup wizard can be imported."""
        try:
            from miniclaw.setup.enhanced_setup_wizard import EnhancedSetupWizard
            self.assertTrue(True)
        except ImportError:
            self.fail("Failed to import EnhancedSetupWizard")

    def test_enhanced_setup_wizard_has_navigation(self):
        """Test that the enhanced setup wizard has navigation features."""
        from miniclaw.setup.enhanced_setup_wizard import EnhancedSetupWizard
        wizard = EnhancedSetupWizard()
        
        # Check that steps are defined
        self.assertTrue(hasattr(wizard, 'steps'))
        self.assertIsInstance(wizard.steps, list)
        self.assertGreater(len(wizard.steps), 0)
        
        # Check for KeyDB installation step
        self.assertIn("KeyDB Installation", wizard.steps)

    def test_enhanced_setup_wizard_file_exists(self):
        """Test that the enhanced setup wizard file exists."""
        setup_file = Path(__file__).parent.parent / "miniclaw" / "setup" / "enhanced_setup_wizard.py"
        self.assertTrue(setup_file.exists(), f"Expected {setup_file} to exist")


if __name__ == "__main__":
    unittest.main()