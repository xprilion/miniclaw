"""Additional unit tests for MiniClaw security features."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from miniclaw.security.security import (
    SandboxManager,
    PermissionManager,
    RateLimiter,
    ContentFilter,
    create_security_managers,
)
from miniclaw.core.config import ConfigStore
from miniclaw.core.events import EventLog


class TestPermissionManagerAdditional(unittest.TestCase):
    """Additional test cases for PermissionManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "tools": {
                        "enabled": True,
                        "allow_shell": True,
                        "allow_filesystem": True,
                    }
                }
            )
        )

        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        self.permissions = PermissionManager(self.config_store, self.event_log)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_request_permission_sensitive_tool_denied(self):
        """Test requesting permission for sensitive tool is denied by default."""
        result = self.permissions.request_permission(
            "run_command", "Testing", "default"
        )
        self.assertFalse(result)

    def test_request_permission_non_sensitive_tool_allowed(self):
        """Test requesting permission for non-sensitive tool is allowed by default."""
        result = self.permissions.request_permission("list_dir", "Testing", "default")
        self.assertTrue(result)

    def test_request_permission_auto_approved(self):
        """Test requesting permission with auto-approval."""
        # Update config to enable auto-approval
        config = self.config_store.get()
        config.setdefault("security", {})["auto_approvals"] = {
            "test_user": ["run_command"]
        }
        self.config_store.save(config)

        result = self.permissions.request_permission(
            "run_command", "Testing", "test_user"
        )
        self.assertTrue(result)

    def test_get_user_groups(self):
        """Test getting user groups."""
        # Update config with user groups
        config = self.config_store.get()
        config.setdefault("security", {})["user_groups"] = {
            "test_user": ["admin", "developer"]
        }
        self.config_store.save(config)

        groups = self.permissions._get_user_groups("test_user")
        self.assertEqual(groups, ["admin", "developer"])

    def test_get_user_groups_no_groups(self):
        """Test getting user groups when none exist."""
        groups = self.permissions._get_user_groups("unknown_user")
        self.assertEqual(groups, [])

    def test_cache_permission(self):
        """Test caching permission results."""
        self.permissions._cache_permission("test_key", True, 12345.0)
        self.assertTrue(self.permissions._permissions_cache["test_key"])
        self.assertEqual(self.permissions._cache_timestamps["test_key"], 12345.0)

    def test_check_tool_permission_with_user_permissions(self):
        """Test checking tool permission with user-specific permissions."""
        # Update config with user-specific permissions
        config = self.config_store.get()
        config["tools"]["user_permissions"] = {
            "test_user": {
                "run_command": False,
                "custom_tool": True,  # Use a tool without feature flags
            }
        }
        self.config_store.save(config)

        # Clear cache to ensure fresh check
        self.permissions._permissions_cache.clear()

        # Test denied permission
        result = self.permissions.check_tool_permission("run_command", "test_user")
        self.assertFalse(result)

        # Test allowed permission
        self.permissions._permissions_cache.clear()
        result = self.permissions.check_tool_permission("custom_tool", "test_user")
        self.assertTrue(result)

    def test_check_tool_permission_with_group_permissions(self):
        """Test checking tool permission with group permissions."""
        # Update config with group permissions
        config = self.config_store.get()
        config.setdefault("security", {})["user_groups"] = {"test_user": ["developers"]}
        config["tools"]["group_permissions"] = {
            "developers": {"custom_tool1": True, "custom_tool2": False}
        }
        self.config_store.save(config)

        # Clear cache to ensure fresh check
        self.permissions._permissions_cache.clear()

        # Test allowed permission
        result = self.permissions.check_tool_permission("custom_tool1", "test_user")
        self.assertTrue(result)

        # Test denied permission - need to clear cache again
        self.permissions._permissions_cache.clear()
        result = self.permissions.check_tool_permission("custom_tool2", "test_user")
        self.assertFalse(result)

    def test_check_tool_permission_with_specific_tool_permissions(self):
        """Test checking tool permission with specific tool permissions."""
        # Update config with specific tool permissions
        config = self.config_store.get()
        config["tools"]["permissions"] = {
            "custom_tool1": {
                "allowed_users": ["admin_user"],
                "allowed_groups": ["admins"],
            },
            "custom_tool2": False,  # Explicitly disabled
        }
        self.config_store.save(config)

        # Clear cache to ensure fresh check
        self.permissions._permissions_cache.clear()

        # Test explicitly disabled tool
        result = self.permissions.check_tool_permission("custom_tool2", "test_user")
        self.assertFalse(result)

        # Test tool with allowed users - user not in allowed list
        self.permissions._permissions_cache.clear()
        result = self.permissions.check_tool_permission("custom_tool1", "test_user")
        self.assertFalse(
            result
        )  # Should be False because test_user is not in allowed_users

    def test_check_tool_permission_admin_user(self):
        """Test that admin users have full access."""
        # Update config to make user an admin
        config = self.config_store.get()
        config.setdefault("security", {})["admin_users"] = ["admin_user"]
        self.config_store.save(config)

        # Admin should have access to everything
        result = self.permissions.check_tool_permission("run_command", "admin_user")
        self.assertTrue(result)

        result = self.permissions.check_tool_permission("write_file", "admin_user")
        self.assertTrue(result)


class TestRateLimiterAdditional(unittest.TestCase):
    """Additional test cases for RateLimiter."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(json.dumps({}))

        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        self.rate_limiter = RateLimiter(self.config_store, self.event_log)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_rate_limit_with_custom_ip_limit(self):
        """Test rate limiting with custom IP limit from config."""
        # Update config with custom IP limit
        config = self.config_store.get()
        config.setdefault("security", {})["ip_rate_limit"] = 5
        self.config_store.save(config)

        # Fill up the limit
        for i in range(5):
            self.assertTrue(
                self.rate_limiter.check_rate_limit(
                    ip_address="192.168.1.100", limit=100, window=60
                )
            )

        # Next request should be blocked due to IP limit
        self.assertFalse(
            self.rate_limiter.check_rate_limit(
                ip_address="192.168.1.100", limit=100, window=60
            )
        )


class TestContentFilterAdditional(unittest.TestCase):
    """Additional test cases for ContentFilter."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(json.dumps({}))

        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        self.content_filter = ContentFilter(self.config_store, self.event_log)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_calculate_entropy(self):
        """Test calculating entropy of text."""
        # Test empty string
        entropy = self.content_filter._calculate_entropy("")
        self.assertEqual(entropy, 0.0)

        # Test string with low entropy (repeated characters)
        entropy = self.content_filter._calculate_entropy("aaaaaa")
        self.assertEqual(entropy, 0.0)

        # Test string with high entropy (random characters)
        entropy = self.content_filter._calculate_entropy("abcdefghijklmnopqrstuvwxyz")
        self.assertGreater(entropy, 3.0)  # Should be high entropy

    def test_looks_like_secret(self):
        """Test determining if text looks like a secret."""
        # Test high entropy string
        result = self.content_filter._looks_like_secret("abcdefghijklmnopqrstuvwxyz")
        self.assertTrue(result)

        # Test long alphanumeric string
        result = self.content_filter._looks_like_secret(
            "sk-1234567890abcdef1234567890abcdef"
        )
        self.assertTrue(result)

        # Test short string
        result = self.content_filter._looks_like_secret("short")
        self.assertFalse(result)

        # Test normal text with spaces
        result = self.content_filter._looks_like_secret("This is normal text")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
