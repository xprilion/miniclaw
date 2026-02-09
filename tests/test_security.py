"""Unit tests for MiniClaw security features."""
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
    create_security_managers
)
from miniclaw.core.config import ConfigStore
from miniclaw.core.events import EventLog


class TestSandboxManager(unittest.TestCase):
    """Test cases for SandboxManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(json.dumps({
            "tools": {
                "working_directory": self.temp_dir
            }
        }))
        
        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        self.sandbox = SandboxManager(self.config_store, self.event_log)
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_validate_safe_command(self):
        """Test validation of safe commands."""
        self.assertTrue(self.sandbox.validate_command("ls -la"))
        self.assertTrue(self.sandbox.validate_command("echo hello"))
        
    def test_block_dangerous_command(self):
        """Test blocking of dangerous commands."""
        self.assertFalse(self.sandbox.validate_command("rm -rf /"))
        self.assertFalse(self.sandbox.validate_command("rm -rf /*"))
        self.assertFalse(self.sandbox.validate_command(":(){ :|:& };:"))
        
    def test_block_command_with_dangerous_patterns(self):
        """Test blocking commands with dangerous patterns."""
        self.assertFalse(self.sandbox.validate_command("ls; rm -rf /"))
        self.assertFalse(self.sandbox.validate_command("echo `rm -rf /`"))
        self.assertFalse(self.sandbox.validate_command("echo $(rm -rf /)"))
        
    def test_validate_safe_file_path(self):
        """Test validation of safe file paths."""
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("test content")
        
        self.assertTrue(self.sandbox.validate_file_path(str(test_file)))
        self.assertTrue(self.sandbox.validate_file_path(str(Path(self.temp_dir) / "nonexistent.txt")))
        
    def test_block_outside_file_path(self):
        """Test blocking of file paths outside workspace."""
        outside_path = "/etc/passwd"
        self.assertFalse(self.sandbox.validate_file_path(outside_path))
        
    def test_sanitize_input(self):
        """Test input sanitization."""
        clean_input = "Hello, world!"
        self.assertEqual(self.sandbox.sanitize_input(clean_input), clean_input)
        
        # Test truncation
        long_input = "x" * 15000
        sanitized = self.sandbox.sanitize_input(long_input, max_length=10000)
        self.assertEqual(len(sanitized), 10000)
        
        # Test null byte removal
        input_with_null = "Hello\x00World"
        sanitized = self.sandbox.sanitize_input(input_with_null)
        self.assertEqual(sanitized, "HelloWorld")


class TestPermissionManager(unittest.TestCase):
    """Test cases for PermissionManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(json.dumps({
            "tools": {
                "enabled": True,
                "allow_shell": True,
                "allow_filesystem": True
            }
        }))
        
        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        self.permissions = PermissionManager(self.config_store, self.event_log)
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_check_tool_permission_allowed(self):
        """Test checking permission for allowed tools."""
        self.assertTrue(self.permissions.check_tool_permission("list_dir"))
        self.assertTrue(self.permissions.check_tool_permission("read_file"))
        
    def test_check_tool_permission_disabled_feature(self):
        """Test checking permission for tools when feature is disabled."""
        # Update config to disable shell commands
        config = self.config_store.get()
        config["tools"]["allow_shell"] = False
        self.config_store.save(config)
        
        self.assertFalse(self.permissions.check_tool_permission("run_command"))
        self.assertTrue(self.permissions.check_tool_permission("list_dir"))
        
    def test_check_tool_permission_globally_disabled(self):
        """Test checking permission when tools are globally disabled."""
        # Update config to disable all tools
        config = self.config_store.get()
        config["tools"]["enabled"] = False
        self.config_store.save(config)
        
        self.assertFalse(self.permissions.check_tool_permission("list_dir"))
        self.assertFalse(self.permissions.check_tool_permission("read_file"))


class TestRateLimiter(unittest.TestCase):
    """Test cases for RateLimiter."""
    
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
        
    def test_allow_under_limit(self):
        """Test allowing requests under rate limit."""
        # Should allow first few requests
        for i in range(5):
            self.assertTrue(self.rate_limiter.check_rate_limit("test_user", limit=10, window=60))
            
    def test_block_over_limit(self):
        """Test blocking requests over rate limit."""
        # Fill up the limit
        for i in range(10):
            self.rate_limiter.check_rate_limit("test_user", limit=10, window=60)
            
        # Next request should be blocked
        self.assertFalse(self.rate_limiter.check_rate_limit("test_user", limit=10, window=60))
        
    def test_ip_rate_limiting(self):
        """Test IP-based rate limiting."""
        # Should allow first few requests from an IP
        for i in range(3):
            self.assertTrue(self.rate_limiter.check_rate_limit(
                ip_address="192.168.1.1", 
                limit=20,  # IP limit is lower
                window=60
            ))
            
        # Next request should be allowed (haven't hit IP limit yet)
        self.assertTrue(self.rate_limiter.check_rate_limit(
            ip_address="192.168.1.1", 
            limit=20, 
            window=60
        ))


class TestContentFilter(unittest.TestCase):
    """Test cases for ContentFilter."""
    
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
        
    def test_filter_api_key(self):
        """Test filtering of API keys."""
        content = "Here's my API key: sk-1234567890abcdef1234567890abcdef1234567890abcdef"
        filtered = self.content_filter.filter_output(content)
        self.assertIn("[REDACTED]", filtered)
        self.assertNotIn("sk-1234567890abcdef1234567890abcdef1234567890abcdef", filtered)
        
    def test_filter_ssn(self):
        """Test filtering of SSN patterns."""
        content = "My SSN is 123-45-6789"
        filtered = self.content_filter.filter_output(content)
        self.assertIn("[REDACTED]", filtered)
        self.assertNotIn("123-45-6789", filtered)
        
    def test_filter_credit_card(self):
        """Test filtering of credit card patterns."""
        content = "My card number is 1234-5678-9012-3456"
        filtered = self.content_filter.filter_output(content)
        self.assertIn("[REDACTED]", filtered)
        self.assertNotIn("1234-5678-9012-3456", filtered)
        
    def test_no_filter_plain_text(self):
        """Test that plain text is not filtered."""
        content = "This is just normal text with no sensitive information."
        filtered = self.content_filter.filter_output(content)
        self.assertEqual(filtered, content)


class TestSecurityManagersFactory(unittest.TestCase):
    """Test cases for security managers factory function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"
        self.config_path.write_text(json.dumps({}))
        
        self.event_log = EventLog()
        self.config_store = ConfigStore(self.config_path, self.event_log)
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_create_security_managers(self):
        """Test creation of all security managers."""
        managers = create_security_managers(self.config_store, self.event_log)
        
        self.assertIn("sandbox", managers)
        self.assertIn("permissions", managers)
        self.assertIn("rate_limiter", managers)
        self.assertIn("content_filter", managers)
        
        self.assertIsInstance(managers["sandbox"], SandboxManager)
        self.assertIsInstance(managers["permissions"], PermissionManager)
        self.assertIsInstance(managers["rate_limiter"], RateLimiter)
        self.assertIsInstance(managers["content_filter"], ContentFilter)


if __name__ == '__main__':
    unittest.main()