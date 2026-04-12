"""Tests for the Python-based web UI."""
import unittest


class TestWebUI(unittest.TestCase):
    """Test that the Python web UI is properly set up."""

    def test_web_app_module_exists(self):
        """Test that the web app module exists."""
        from miniclaw.web import app
        self.assertIsNotNone(app)

    def test_create_app_function_exists(self):
        """Test that create_app function exists."""
        from miniclaw.web.app import create_app
        self.assertTrue(callable(create_app))

    def test_templates_exist(self):
        """Test that Jinja2 templates exist."""
        from pathlib import Path
        template_dir = Path(__file__).parent.parent / "miniclaw" / "web" / "templates"
        self.assertTrue(template_dir.exists())
        
        base_template = template_dir / "base.html"
        monitoring_template = template_dir / "monitoring.html"
        
        self.assertTrue(base_template.exists(), "base.html should exist")
        self.assertTrue(monitoring_template.exists(), "monitoring.html should exist")

    def test_no_preact_frontend(self):
        """Test that preact frontend directory has been removed."""
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        frontend_dir = project_root / "frontend"
        self.assertFalse(frontend_dir.exists(), "frontend directory should not exist")

    def test_no_web_built(self):
        """Test that web-built directory has been removed."""
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        web_built_dir = project_root / "web-built"
        self.assertFalse(web_built_dir.exists(), "web-built directory should not exist")


if __name__ == "__main__":
    unittest.main()