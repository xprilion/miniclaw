"""Test CLI service management functionality."""

import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os
from pathlib import Path

# Import the service management functions directly
from miniclaw.cli.cli import (
    manage_linux_service,
    manage_macos_service,
    manage_windows_service,
    run_install_service,
    run_uninstall_service,
)


class TestCLIServiceManagement(unittest.TestCase):
    """Test service management functionality."""

    @patch("subprocess.run")
    def test_manage_linux_service_start_already_active(self, mock_subprocess):
        """Test starting Linux service when it's already active."""
        # Mock systemctl is-active to return "active"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "active\n"
        mock_subprocess.return_value = mock_result

        result = manage_linux_service("start")
        self.assertEqual(result, 0)
        mock_subprocess.assert_called_with(
            ["systemctl", "is-active", "miniclaw"], capture_output=True, text=True
        )

    @patch("subprocess.run")
    def test_manage_linux_service_start_success(self, mock_subprocess):
        """Test successfully starting Linux service."""
        # First call (is-active) returns non-zero (not active)
        # Second call (start) succeeds
        mock_result1 = MagicMock()
        mock_result1.returncode = 1  # Not active
        mock_result1.stdout = "inactive\n"

        mock_result2 = MagicMock()
        mock_result2.returncode = 0  # Start succeeds

        mock_subprocess.side_effect = [mock_result1, mock_result2]

        result = manage_linux_service("start")
        self.assertEqual(result, 0)
        self.assertEqual(mock_subprocess.call_count, 2)

    @patch("subprocess.run")
    def test_manage_linux_service_stop_success(self, mock_subprocess):
        """Test successfully stopping Linux service."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        result = manage_linux_service("stop")
        self.assertEqual(result, 0)
        mock_subprocess.assert_called_with(
            ["sudo", "systemctl", "stop", "miniclaw"], check=True
        )

    @patch("subprocess.run")
    def test_manage_linux_service_restart_success(self, mock_subprocess):
        """Test successfully restarting Linux service."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        result = manage_linux_service("restart")
        self.assertEqual(result, 0)
        mock_subprocess.assert_called_with(
            ["sudo", "systemctl", "restart", "miniclaw"], check=True
        )

    @patch("subprocess.run")
    def test_manage_linux_service_status_active(self, mock_subprocess):
        """Test checking status of active Linux service."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "active\n"
        mock_subprocess.return_value = mock_result

        result = manage_linux_service("status")
        self.assertEqual(result, 0)
        mock_subprocess.assert_called_with(
            ["systemctl", "is-active", "miniclaw"], capture_output=True, text=True
        )

    @patch("subprocess.run")
    def test_manage_linux_service_status_inactive(self, mock_subprocess):
        """Test checking status of inactive Linux service."""
        mock_result = MagicMock()
        mock_result.returncode = 1  # Not active
        mock_result.stdout = "inactive\n"
        mock_subprocess.return_value = mock_result

        result = manage_linux_service("status")
        self.assertEqual(result, 0)
        mock_subprocess.assert_called_with(
            ["systemctl", "is-active", "miniclaw"], capture_output=True, text=True
        )

    @patch("subprocess.run")
    def test_manage_linux_service_with_exception(self, mock_subprocess):
        """Test handling exceptions in Linux service management."""
        mock_subprocess.side_effect = Exception("System error")

        result = manage_linux_service("start")
        self.assertEqual(result, 1)

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_manage_macos_service_start_success(self, mock_exists, mock_subprocess):
        """Test successfully starting macOS service."""
        mock_exists.return_value = True  # Plist file exists

        # Mock launchctl list to show service is not loaded
        mock_result1 = MagicMock()
        mock_result1.returncode = 1  # Not loaded
        mock_result1.stdout = ""

        mock_result2 = MagicMock()
        mock_result2.returncode = 0  # Load succeeds

        mock_subprocess.side_effect = [mock_result1, mock_result2]

        result = manage_macos_service("start")
        self.assertEqual(result, 0)

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_manage_macos_service_start_not_installed(
        self, mock_exists, mock_subprocess
    ):
        """Test starting macOS service when not installed."""
        mock_exists.return_value = False  # Plist file doesn't exist

        result = manage_macos_service("start")
        self.assertEqual(result, 1)

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_manage_macos_service_stop_success(self, mock_exists, mock_subprocess):
        """Test successfully stopping macOS service."""
        mock_exists.return_value = True

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        result = manage_macos_service("stop")
        self.assertEqual(result, 0)
        mock_subprocess.assert_called_with(
            [
                "launchctl",
                "unload",
                str(
                    Path.home()
                    / "Library"
                    / "LaunchAgents"
                    / "com.miniclaw.agent.plist"
                ),
            ],
            check=True,
        )

    @patch("subprocess.run")
    def test_manage_windows_service_start_success(self, mock_subprocess):
        """Test successfully starting Windows service."""
        # Mock sc query to show service exists
        mock_result1 = MagicMock()
        mock_result1.returncode = 0
        mock_result1.stdout = "STATE: 1 STOPPED"

        mock_result2 = MagicMock()
        mock_result2.returncode = 0  # Start succeeds

        mock_subprocess.side_effect = [mock_result1, mock_result2]

        result = manage_windows_service("start")
        self.assertEqual(result, 0)

    @patch("subprocess.run")
    def test_manage_windows_service_start_not_installed(self, mock_subprocess):
        """Test starting Windows service when not installed."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "does not exist"
        mock_subprocess.return_value = mock_result

        result = manage_windows_service("start")
        self.assertEqual(result, 1)

    @patch("subprocess.run")
    def test_manage_windows_service_stop_success(self, mock_subprocess):
        """Test successfully stopping Windows service."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        result = manage_windows_service("stop")
        self.assertEqual(result, 0)
        mock_subprocess.assert_called_with(["sc", "stop", "MiniClaw"], check=True)

    @patch("subprocess.run")
    @patch("platform.system")
    def test_run_uninstall_service_linux(self, mock_platform, mock_subprocess):
        """Test uninstalling Linux service."""
        mock_platform.return_value = "Linux"

        # Mock all subprocess calls to succeed
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        result = run_uninstall_service(MagicMock())
        self.assertEqual(result, 0)

    @patch("pathlib.Path.unlink")
    @patch("pathlib.Path.exists")
    @patch("subprocess.run")
    @patch("platform.system")
    def test_run_uninstall_service_macos(
        self, mock_platform, mock_subprocess, mock_exists, mock_unlink
    ):
        """Test uninstalling macOS service."""
        mock_platform.return_value = "Darwin"
        mock_exists.return_value = True  # Plist file exists
        mock_unlink.return_value = None  # Mock successful file deletion

        # Mock subprocess calls to succeed
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        result = run_uninstall_service(MagicMock())
        self.assertEqual(result, 0)

    @patch("subprocess.run")
    @patch("platform.system")
    def test_run_uninstall_service_windows(self, mock_platform, mock_subprocess):
        """Test uninstalling Windows service."""
        mock_platform.return_value = "Windows"

        # Mock subprocess calls to succeed
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        result = run_uninstall_service(MagicMock())
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
