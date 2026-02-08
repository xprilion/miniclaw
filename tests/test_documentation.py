"""Test documentation completeness and accuracy."""
import unittest
from pathlib import Path


class TestDocumentation(unittest.TestCase):
    """Test documentation files exist and are properly linked."""

    def test_main_docs_exist(self):
        """Test that main documentation files exist."""
        docs_dir = Path(__file__).parent.parent / "docs"
        
        # Core documentation files
        required_files = [
            "cli.md",
            "cli_styling.md", 
            "setup.md"
        ]
        
        for filename in required_files:
            file_path = docs_dir / filename
            self.assertTrue(file_path.exists(), f"Documentation file {filename} should exist")
    
    def test_readme_links_updated(self):
        """Test that README.md has been updated with new documentation links."""
        readme_path = Path(__file__).parent.parent / "README.md"
        content = readme_path.read_text()
        
        # Should reference new documentation files
        self.assertIn("cli.md", content)
        self.assertIn("setup.md", content)
        self.assertIn("cli_styling.md", content)
        
        # Should have comprehensive CLI reference
        self.assertIn("miniclaw jobs", content)
        self.assertIn("miniclaw memory", content)
        self.assertIn("miniclaw providers", content)
    
    def test_getting_started_updated(self):
        """Test that getting started guide mentions new features."""
        getting_started_path = Path(__file__).parent.parent / "docs" / "getting_started.md"
        content = getting_started_path.read_text()
        
        # Should mention enhanced features
        self.assertIn("Interactive Setup Wizard", content)
        self.assertIn("Consistent CLI Styling", content)
        self.assertIn("cli_styling.md", content)
    
    def test_architecture_updated(self):
        """Test that architecture documentation mentions CLI."""
        architecture_path = Path(__file__).parent.parent / "docs" / "architecture.md"
        content = architecture_path.read_text()
        
        # Should have CLI section
        self.assertIn("Command Line Interface", content)
    
    def test_api_docs_updated(self):
        """Test that API documentation mentions CLI equivalents."""
        api_path = Path(__file__).parent.parent / "docs" / "api.md"
        content = api_path.read_text()
        
        # Should mention CLI documentation
        self.assertIn("cli.md", content)
    
    def test_docs_directory_structure(self):
        """Test that docs directory has expected structure."""
        docs_dir = Path(__file__).parent.parent / "docs"
        self.assertTrue(docs_dir.exists(), "Docs directory should exist")
        
        # List all markdown files
        md_files = list(docs_dir.glob("*.md"))
        self.assertGreater(len(md_files), 5, "Should have multiple documentation files")


if __name__ == "__main__":
    unittest.main()