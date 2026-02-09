"""Test the CLI module functionality."""

import json
import unittest
from unittest.mock import patch, MagicMock
from miniclaw.cli.cli import parse_json, request_json, run_gateway_service


class TestCLIModule(unittest.TestCase):
    """Test CLI module functionality."""

    def test_parse_json_with_valid_json(self):
        """Test parsing valid JSON string."""
        text = '{"key": "value", "number": 42}'
        result = parse_json(text)
        self.assertEqual(result, {"key": "value", "number": 42})

    def test_parse_json_with_invalid_json(self):
        """Test parsing invalid JSON string."""
        text = '{"key": "value", "number": 42'  # Missing closing brace
        result = parse_json(text)
        self.assertEqual(result, {"raw": text})

    def test_parse_json_with_empty_string(self):
        """Test parsing empty string."""
        text = ""
        result = parse_json(text)
        self.assertEqual(result, {})

    def test_parse_json_with_whitespace_only(self):
        """Test parsing whitespace-only string."""
        text = "   \n\t  "
        result = parse_json(text)
        self.assertEqual(result, {})

    @patch("urllib.request.urlopen")
    def test_request_json_get_success(self, mock_urlopen):
        """Test successful GET request."""
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value.decode.return_value = '{"result": "success"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = request_json("http://localhost:8000", "/api/test")
        self.assertEqual(result, {"result": "success"})

    @patch("urllib.request.urlopen")
    def test_request_json_post_with_payload(self, mock_urlopen):
        """Test POST request with JSON payload."""
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value.decode.return_value = '{"status": "created"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        payload = {"name": "test", "value": 123}
        result = request_json(
            "http://localhost:8000", "/api/test", method="POST", payload=payload
        )
        self.assertEqual(result, {"status": "created"})

    @patch("urllib.request.urlopen")
    def test_request_json_with_http_error(self, mock_urlopen):
        """Test handling of HTTP errors."""
        from urllib.error import HTTPError

        # Mock HTTP error
        mock_error = HTTPError(
            "http://localhost:8000/api/test", 404, "Not Found", {}, None
        )
        mock_error.read = MagicMock(return_value=b'{"error": "Resource not found"}')
        mock_urlopen.side_effect = mock_error

        with self.assertRaises(RuntimeError) as context:
            request_json("http://localhost:8000", "/api/test")

        self.assertIn("HTTP 404: Resource not found", str(context.exception))

    @patch("urllib.request.urlopen")
    def test_request_json_with_network_error(self, mock_urlopen):
        """Test handling of network errors."""
        from urllib.error import URLError

        # Mock network error
        mock_urlopen.side_effect = URLError("Connection refused")

        with self.assertRaises(RuntimeError) as context:
            request_json("http://localhost:8000", "/api/test")

        self.assertIn("Network error:", str(context.exception))

    @patch("platform.system")
    @patch("miniclaw.cli.cli.manage_linux_service")
    def test_run_gateway_service_linux(self, mock_manage_linux, mock_platform):
        """Test running gateway service on Linux."""
        mock_platform.return_value = "Linux"
        mock_manage_linux.return_value = 0

        # Create a mock args object
        args = MagicMock()
        args.gateway_command = "start"

        result = run_gateway_service(args)
        self.assertEqual(result, 0)
        mock_manage_linux.assert_called_once_with("start")

    @patch("platform.system")
    @patch("miniclaw.cli.cli.manage_macos_service")
    def test_run_gateway_service_macos(self, mock_manage_macos, mock_platform):
        """Test running gateway service on macOS."""
        mock_platform.return_value = "Darwin"
        mock_manage_macos.return_value = 0

        # Create a mock args object
        args = MagicMock()
        args.gateway_command = "start"

        result = run_gateway_service(args)
        self.assertEqual(result, 0)
        mock_manage_macos.assert_called_once_with("start")

    @patch("platform.system")
    @patch("miniclaw.cli.cli.manage_windows_service")
    def test_run_gateway_service_windows(self, mock_manage_windows, mock_platform):
        """Test running gateway service on Windows."""
        mock_platform.return_value = "Windows"
        mock_manage_windows.return_value = 0

        # Create a mock args object
        args = MagicMock()
        args.gateway_command = "start"

        result = run_gateway_service(args)
        self.assertEqual(result, 0)
        mock_manage_windows.assert_called_once_with("start")

    @patch("platform.system")
    def test_run_gateway_service_unsupported_os(self, mock_platform):
        """Test running gateway service on unsupported OS."""
        mock_platform.return_value = "FreeBSD"

        # Create a mock args object
        args = MagicMock()
        args.gateway_command = "start"

        result = run_gateway_service(args)
        self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
