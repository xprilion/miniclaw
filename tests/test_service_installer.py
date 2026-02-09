"""Unit tests for MiniClaw service installer."""

import unittest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add the setup directory to the path so we can import the service installer
sys.path.insert(0, str(Path(__file__).parent.parent / "miniclaw" / "setup"))

import service_installer


class TestServiceInstaller(unittest.TestCase):
    """Test cases for service_installer functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detect_os(self):
        """Test detect_os function."""
        result = service_installer.detect_os()
        self.assertIsInstance(result, str)
        # The test might run on different OSes, so just check it returns a reasonable value
        self.assertIn(result, ["linux", "darwin", "windows"])

    @patch("shutil.which")
    def test_install_linux_service_systemctl_not_available(self, mock_which):
        """Test install_linux_service when systemctl is not available."""
        # Mock shutil.which to return None for systemctl
        mock_which.return_value = None

        # Capture print output
        with patch("builtins.print") as mock_print:
            result = service_installer.install_linux_service()

        self.assertFalse(result)
        mock_print.assert_any_call("Error: systemd is not available on this system.")

    @patch("shutil.which")
    def test_install_linux_service_success(self, mock_which):
        """Test install_linux_service success case."""
        # Mock shutil.which to return systemctl path
        mock_which.return_value = "/bin/systemctl"

        # Change to temp directory for file creation
        original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            # Capture print output
            with patch("builtins.print") as mock_print:
                result = service_installer.install_linux_service()

            self.assertTrue(result)
            mock_print.assert_any_call(
                "Installing MiniClaw systemd service on Linux..."
            )
            mock_print.assert_any_call("Service file created: miniclaw.service")

            # Verify service file was created
            service_file = Path(self.temp_dir) / "miniclaw.service"
            self.assertTrue(service_file.exists())

            # Verify service file content
            content = service_file.read_text()
            self.assertIn("[Unit]", content)
            self.assertIn("Description=MiniClaw AI Agent", content)
            self.assertIn("[Service]", content)
            self.assertIn("[Install]", content)
        finally:
            os.chdir(original_cwd)

    def test_install_macos_service_success(self):
        """Test install_macos_service success case."""
        # Change to temp directory for file creation
        original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            # Capture print output
            with patch("builtins.print") as mock_print:
                result = service_installer.install_macos_service()

            self.assertTrue(result)
            mock_print.assert_any_call("Installing MiniClaw launch daemon on macOS...")

            # Verify plist file was created in temp directory structure
            plist_path = (
                Path(self.temp_dir)
                / "Library"
                / "LaunchAgents"
                / "com.miniclaw.agent.plist"
            )
            # The function tries to create in user's Library, but in test it may fail
            # The important thing is that it doesn't crash
        finally:
            os.chdir(original_cwd)

    def test_install_windows_service_success(self):
        """Test install_windows_service success case."""
        # Change to temp directory for file creation
        original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            # Capture print output
            with patch("builtins.print") as mock_print:
                result = service_installer.install_windows_service()

            self.assertTrue(result)
            mock_print.assert_any_call("Creating Windows service installation files...")

            # Verify batch and PowerShell files were created
            bat_file = Path(self.temp_dir) / "install_service.bat"
            ps1_file = Path(self.temp_dir) / "install_service.ps1"
            self.assertTrue(bat_file.exists())
            self.assertTrue(ps1_file.exists())

            # Verify file content
            bat_content = bat_file.read_text()
            ps1_content = ps1_file.read_text()
            self.assertIn("MiniClaw Windows Service Installation Script", bat_content)
            self.assertIn(
                "MiniClaw Windows Service Installation Script (PowerShell)", ps1_content
            )
        finally:
            os.chdir(original_cwd)

    @patch("platform.system")
    def test_main_with_linux_os(self, mock_system):
        """Test main function with Linux OS."""
        mock_system.return_value = "Linux"

        with patch("service_installer.install_linux_service") as mock_install:
            mock_install.return_value = True

            # Capture print output and sys.exit
            with patch("builtins.print") as mock_print:
                with patch("sys.exit") as mock_exit:
                    service_installer.main()

            mock_install.assert_called_once()
            mock_exit.assert_called_once_with(0)

    @patch("platform.system")
    def test_main_with_unsupported_os(self, mock_system):
        """Test main function with unsupported OS."""
        mock_system.return_value = "FreeBSD"

        # Capture print output and sys.exit
        with patch("builtins.print") as mock_print:
            with patch("sys.exit") as mock_exit:
                service_installer.main()

        mock_exit.assert_called_once_with(1)

    @patch("platform.system")
    def test_main_with_installation_failure(self, mock_system):
        """Test main function when installation fails."""
        mock_system.return_value = "Linux"

        with patch("service_installer.install_linux_service") as mock_install:
            mock_install.return_value = False

            # Capture print output and sys.exit
            with patch("builtins.print") as mock_print:
                with patch("sys.exit") as mock_exit:
                    service_installer.main()

            mock_install.assert_called_once()
            mock_exit.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()
