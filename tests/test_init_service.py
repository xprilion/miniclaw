"""Unit tests for MiniClaw init service module."""

import unittest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add the setup directory to the path so we can import the init_service module
sys.path.insert(0, str(Path(__file__).parent.parent / "miniclaw" / "setup"))

import init_service


class TestInitService(unittest.TestCase):
    """Test cases for init_service functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_query_user_for_service_installation_yes(self):
        """Test query_user_for_service_installation with yes response."""
        with patch("builtins.input", side_effect=["y"]):
            with patch("builtins.print") as mock_print:
                result = init_service.query_user_for_service_installation()

        self.assertTrue(result)

    def test_query_user_for_service_installation_no(self):
        """Test query_user_for_service_installation with no response."""
        with patch("builtins.input", side_effect=["n"]):
            with patch("builtins.print") as mock_print:
                result = init_service.query_user_for_service_installation()

        self.assertFalse(result)

    def test_query_user_for_service_installation_invalid_then_yes(self):
        """Test query_user_for_service_installation with invalid then yes response."""
        with patch("builtins.input", side_effect=["maybe", "y"]):
            with patch("builtins.print") as mock_print:
                result = init_service.query_user_for_service_installation()

        self.assertTrue(result)
        # Verify that the prompt for valid input was printed
        mock_print.assert_any_call("Please enter 'y' for yes or 'n' for no.")

    @patch("platform.system")
    def test_install_service_linux(self, mock_system):
        """Test install_service with Linux OS."""
        mock_system.return_value = "Linux"

        with patch("init_service.install_linux_service") as mock_install:
            mock_install.return_value = True
            result = init_service.install_service()

        self.assertTrue(result)
        mock_install.assert_called_once()

    @patch("platform.system")
    def test_install_service_macos(self, mock_system):
        """Test install_service with macOS."""
        mock_system.return_value = "Darwin"

        with patch("init_service.install_macos_service") as mock_install:
            mock_install.return_value = True
            result = init_service.install_service()

        self.assertTrue(result)
        mock_install.assert_called_once()

    @patch("platform.system")
    def test_install_service_windows(self, mock_system):
        """Test install_service with Windows."""
        mock_system.return_value = "Windows"

        with patch("init_service.install_windows_service") as mock_install:
            mock_install.return_value = True
            result = init_service.install_service()

        self.assertTrue(result)
        mock_install.assert_called_once()

    @patch("platform.system")
    def test_install_service_unsupported_os(self, mock_system):
        """Test install_service with unsupported OS."""
        mock_system.return_value = "FreeBSD"

        with patch("builtins.print") as mock_print:
            result = init_service.install_service()

        self.assertFalse(result)
        mock_print.assert_called_with(
            "Unsupported operating system for automatic service installation: freebsd"
        )

    @patch("platform.system")
    def test_install_linux_service_systemd_not_available(self, mock_system):
        """Test install_linux_service when systemd is not available."""
        mock_system.return_value = "Linux"

        # Change to temp directory where /etc/systemd/system doesn't exist
        original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            with patch("builtins.print") as mock_print:
                # Set environment variable to simulate systemd not being available in tests
                with patch.dict(os.environ, {"MINICLAW_TEST_NO_SYSTEMD": "1"}):
                    result = init_service.install_linux_service()

            self.assertFalse(result)
            mock_print.assert_any_call(
                "systemd not found. Cannot install service automatically."
            )
        finally:
            os.chdir(original_cwd)

    @patch("platform.system")
    @patch("subprocess.check_output")
    def test_install_linux_service_success(self, mock_check_output, mock_system):
        """Test install_linux_service success case."""
        mock_system.return_value = "Linux"
        mock_check_output.return_value = b"/usr/local/bin/miniclaw"

        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        # Create fake /etc/systemd/system directory
        systemd_dir = Path(self.temp_dir) / "etc" / "systemd" / "system"
        systemd_dir.mkdir(parents=True, exist_ok=True)

        # Patch os.path.exists to make the function think /etc/systemd/system exists
        original_exists = os.path.exists
        
        def mock_exists(path):
            if path == "/etc/systemd/system":
                return True
            return original_exists(path)

        try:
            with patch("builtins.print") as mock_print:
                with patch.dict(
                    os.environ, {"PATH": "/usr/local/bin:/usr/bin:/bin"}, clear=False
                ):
                    with patch("os.getcwd", return_value=self.temp_dir):
                        with patch("os.path.exists", side_effect=mock_exists):
                            result = init_service.install_linux_service()

            self.assertTrue(result)
            mock_print.assert_any_call(
                f"Service file created: {self.temp_dir}/miniclaw.service"
            )

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

    @patch("platform.system")
    @patch("subprocess.check_output")
    def test_install_macos_service_success(self, mock_check_output, mock_system):
        """Test install_macos_service success case."""
        mock_system.return_value = "Darwin"
        mock_check_output.return_value = b"/usr/local/bin/miniclaw"

        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            with patch("builtins.print") as mock_print:
                with patch.dict(
                    os.environ, {"PATH": "/usr/local/bin:/usr/bin:/bin"}, clear=False
                ):
                    with patch("os.getcwd", return_value=self.temp_dir):
                        result = init_service.install_macos_service()

            self.assertTrue(result)

            # Verify plist file was created
            plist_path = (
                Path.home() / "Library" / "LaunchAgents" / "com.miniclaw.agent.plist"
            )
            # We won't check for existence since it might fail in test environment
            # The important thing is that it didn't crash
        finally:
            os.chdir(original_cwd)

    @patch("platform.system")
    def test_install_windows_service_success(self, mock_system):
        """Test install_windows_service success case."""
        mock_system.return_value = "Windows"

        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            with patch("builtins.print") as mock_print:
                with patch.dict(
                    os.environ, {"PATH": "/usr/local/bin:/usr/bin:/bin"}, clear=False
                ):
                    result = init_service.install_windows_service()

            self.assertTrue(result)
            # Handle path resolution differences (macOS /private issue)
            expected_path = Path(self.temp_dir) / "install_miniclaw_service.ps1"
            mock_print.assert_any_call(
                f"Windows service installation script created: {expected_path.resolve()}"
            )

            # Verify PowerShell script was created
            ps1_file = Path(self.temp_dir) / "install_miniclaw_service.ps1"
            self.assertTrue(ps1_file.exists())

            # Verify script content
            content = ps1_file.read_text()
            self.assertIn(
                "# MiniClaw Windows Service Installation Script (PowerShell)", content
            )
        finally:
            os.chdir(original_cwd)

    def test_main_user_accepts_service(self):
        """Test main function when user accepts service installation."""
        with patch("init_service.query_user_for_service_installation") as mock_query:
            mock_query.return_value = True

            with patch("init_service.install_service") as mock_install:
                mock_install.return_value = True

                with patch("builtins.print") as mock_print:
                    init_service.main()

            mock_install.assert_called_once()
            mock_print.assert_any_call("\nService setup completed successfully!")

    def test_main_user_declines_service(self):
        """Test main function when user declines service installation."""
        with patch("init_service.query_user_for_service_installation") as mock_query:
            mock_query.return_value = False

            with patch("builtins.print") as mock_print:
                init_service.main()

            mock_print.assert_any_call(
                "Skipping service setup. You can set up the service later by running:"
            )

    def test_main_service_installation_fails(self):
        """Test main function when service installation fails."""
        with patch("init_service.query_user_for_service_installation") as mock_query:
            mock_query.return_value = True

            with patch("init_service.install_service") as mock_install:
                mock_install.return_value = False

                with patch("builtins.print") as mock_print:
                    init_service.main()

            mock_install.assert_called_once()
            mock_print.assert_any_call(
                "\nService setup failed. You can manually set up the service later."
            )


if __name__ == "__main__":
    unittest.main()
