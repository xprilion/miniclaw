"""Unit tests for MiniClaw setup wizard."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from miniclaw.setup.setup_wizard import SetupWizard


class TestSetupWizard(unittest.TestCase):
    """Test cases for SetupWizard."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_dir = Path(self.temp_dir) / ".miniclaw"
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    @patch('miniclaw.setup.setup_wizard.SetupWizard._check_prerequisites')
    @patch('miniclaw.setup.setup_wizard.SetupWizard._create_workspace')
    @patch('miniclaw.setup.setup_wizard.SetupWizard._configure_model_provider')
    @patch('miniclaw.setup.setup_wizard.SetupWizard._configure_telegram')
    @patch('miniclaw.setup.setup_wizard.SetupWizard._create_default_config')
    @patch('miniclaw.setup.setup_wizard.SetupWizard._create_default_files')
    def test_run_success(self, mock_create_files, mock_create_config, mock_configure_telegram, 
                        mock_configure_provider, mock_create_workspace, mock_check_prerequisites):
        """Test successful setup wizard run."""
        # Configure mocks
        mock_check_prerequisites.return_value = True
        mock_configure_provider.return_value = {
            "id": "ollama_default",
            "name": "Ollama Default",
            "type": "ollama",
            "enabled": True,
            "base_url": "http://localhost:11434",
            "api_key": "",
            "model": "qwen3",
            "temperature": 0.2,
            "timeout_seconds": 300,
            "verify_tls": True,
            "system_prompt_override": "",
        }
        mock_configure_telegram.return_value = None
        
        # Create setup wizard with test workspace
        with patch('miniclaw.setup.setup_wizard.WORKSPACE_DIR', self.workspace_dir):
            with patch('miniclaw.setup.setup_wizard.CONFIG_PATH', self.workspace_dir / "miniclaw_config.json"):
                wizard = SetupWizard()
                result = wizard.run()
                
        # Verify success
        self.assertTrue(result)
        
        # Verify all steps were called
        mock_check_prerequisites.assert_called_once()
        mock_create_workspace.assert_called_once()
        mock_configure_provider.assert_called_once()
        mock_configure_telegram.assert_called_once()
        mock_create_config.assert_called_once()
        mock_create_files.assert_called_once()
        
    def test_check_prerequisites_python_version(self):
        """Test prerequisite check for Python version."""
        with patch('miniclaw.setup.setup_wizard.sys.version_info', (3, 9, 0)):
            wizard = SetupWizard()
            result = wizard._check_prerequisites()
            self.assertTrue(result)
            
        with patch('miniclaw.setup.setup_wizard.sys.version_info', (3, 8, 0)):
            wizard = SetupWizard()
            result = wizard._check_prerequisites()
            self.assertFalse(result)
            
    def test_check_prerequisites_package_manager(self):
        """Test prerequisite check for package managers."""
        # Test with uv available
        with patch('miniclaw.setup.setup_wizard.shutil.which', side_effect=lambda x: x == 'uv'):
            wizard = SetupWizard()
            result = wizard._check_prerequisites()
            self.assertTrue(result)
            
        # Test with pip available
        with patch('miniclaw.setup.setup_wizard.shutil.which', side_effect=lambda x: x == 'pip'):
            wizard = SetupWizard()
            result = wizard._check_prerequisites()
            self.assertTrue(result)
            
        # Test with neither available
        with patch('miniclaw.setup.setup_wizard.shutil.which', return_value=None):
            wizard = SetupWizard()
            result = wizard._check_prerequisites()
            self.assertFalse(result)
            
    def test_create_workspace(self):
        """Test workspace creation."""
        with patch('miniclaw.setup.setup_wizard.WORKSPACE_DIR', self.workspace_dir):
            wizard = SetupWizard()
            wizard._create_workspace()
            
        # Verify directories were created
        self.assertTrue(self.workspace_dir.exists())
        self.assertTrue((self.workspace_dir / "memory").exists())
        self.assertTrue((self.workspace_dir / "skills").exists())
        self.assertTrue((self.workspace_dir / "plugins").exists())
        self.assertTrue((self.workspace_dir / "jobs").exists())
        
    def test_configure_ollama_provider(self):
        """Test Ollama provider configuration."""
        wizard = SetupWizard()
        
        # Test with mocked subprocess
        with patch('miniclaw.setup.setup_wizard.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = wizard._configure_ollama()
            
        # Verify result structure
        self.assertIsNotNone(result)
        if result is not None:
            self.assertEqual(result["id"], "ollama_default")
            self.assertEqual(result["type"], "ollama")
            self.assertTrue(result["enabled"])
            self.assertIn("base_url", result)
            self.assertIn("model", result)
        
    def test_configure_openai_provider(self):
        """Test OpenAI provider configuration."""
        wizard = SetupWizard()
        
        # Test with mocked input
        with patch('miniclaw.setup.setup_wizard.input', side_effect=['test-api-key', 'gpt-4']):
            result = wizard._configure_openai()
            
        # Verify result structure
        self.assertIsNotNone(result)
        if result is not None:
            self.assertEqual(result["id"], "openai_default")
            self.assertEqual(result["type"], "openai_compatible")
            self.assertTrue(result["enabled"])
            self.assertEqual(result["api_key"], "test-api-key")
            self.assertEqual(result["model"], "gpt-4")
        
    def test_configure_openrouter_provider(self):
        """Test OpenRouter provider configuration."""
        wizard = SetupWizard()
        
        # Test with mocked input
        with patch('miniclaw.setup.setup_wizard.input', side_effect=['test-api-key', 'openai/gpt-4']):
            result = wizard._configure_openrouter()
            
        # Verify result structure
        self.assertIsNotNone(result)
        if result is not None:
            self.assertEqual(result["id"], "openrouter_default")
            self.assertEqual(result["type"], "openrouter")
            self.assertTrue(result["enabled"])
            self.assertEqual(result["api_key"], "test-api-key")
            self.assertEqual(result["model"], "openai/gpt-4")
        
    def test_create_default_config(self):
        """Test default configuration creation."""
        config_path = self.workspace_dir / "miniclaw_config.json"
        
        with patch('miniclaw.setup.setup_wizard.WORKSPACE_DIR', self.workspace_dir):
            with patch('miniclaw.setup.setup_wizard.CONFIG_PATH', config_path):
                wizard = SetupWizard()
                
                provider_config = {
                    "id": "test_provider",
                    "name": "Test Provider",
                    "type": "ollama",
                    "enabled": True,
                    "base_url": "http://localhost:11434",
                    "api_key": "",
                    "model": "test-model",
                    "temperature": 0.2,
                    "timeout_seconds": 300,
                    "verify_tls": True,
                    "system_prompt_override": "",
                }
                
                wizard._create_default_config(provider_config, None)
                
        # Verify config file was created
        self.assertTrue(config_path.exists())
        
        # Verify config content
        config_content = json.loads(config_path.read_text())
        self.assertIn("server", config_content)
        self.assertIn("providers", config_content)
        self.assertIn("telegram", config_content)
        self.assertIn("tools", config_content)
        
        # Verify provider config
        self.assertEqual(len(config_content["providers"]["items"]), 1)
        self.assertEqual(config_content["providers"]["items"][0]["id"], "test_provider")
        
    def test_create_default_files(self):
        """Test default files creation."""
        memory_dir = self.workspace_dir / "memory"
        skills_dir = self.workspace_dir / "skills"
        
        with patch('miniclaw.setup.setup_wizard.WORKSPACE_DIR', self.workspace_dir):
            wizard = SetupWizard()
            wizard._create_default_files()
            
        # Verify memory files were created
        self.assertTrue((memory_dir / "soul.md").exists())
        self.assertTrue((memory_dir / "user.md").exists())
        self.assertTrue((memory_dir / "project.md").exists())
        self.assertTrue((memory_dir / "journal.md").exists())
        
        # Verify skill files were created
        self.assertTrue((skills_dir / "issue_triage.md").exists())
        self.assertTrue((skills_dir / "research_compare.md").exists())
        self.assertTrue((skills_dir / "ship_plan.md").exists())


if __name__ == '__main__':
    unittest.main()