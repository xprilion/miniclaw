"""Security utilities for MiniClaw: sandboxing, permission controls, and input validation."""
from __future__ import annotations

import hashlib
import math
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from .config import ConfigStore
from .events import EventLog
from .util import LOGGER


class SandboxManager:
    """Manages secure execution environments for tools."""
    
    def __init__(self, config_store: ConfigStore, event_log: EventLog) -> None:
        self._config_store = config_store
        self._event_log = event_log
        self._allowed_paths: Set[str] = set()
        self._blocked_commands: Set[str] = {
            # Dangerous commands that should never be executed
            "rm", "mkfs", "dd", "chmod", "chown", "wget", "curl", "nc", "netcat", "telnet",
            "ssh", "scp", "rsync", "ftp", "sftp", "mount", "umount", "killall",
            "shutdown", "reboot", "halt", "poweroff"
        }
        # Commands that require special permissions
        self._restricted_commands: Set[str] = {
            "sudo", "su", "passwd", "useradd", "userdel", "groupadd", "groupdel",
            "iptables", "ufw", "firewall-cmd", "systemctl", "service", "crontab",
            "at", "batch", "yum", "apt", "apt-get", "dnf", "pacman"
        }
        
    def validate_command(self, command: str, cwd: str = "", user_id: str = "default") -> bool:
        """Validate that a command is safe to execute."""
        command = command.strip()
        if not command:
            return False
            
        # Check if command is in blocked list
        cmd_parts = command.split()
        if not cmd_parts:
            return False
            
        base_cmd = cmd_parts[0].lower()
        if base_cmd in self._blocked_commands:
            self._event_log.add(
                "security.command.blocked",
                "Blocked dangerous command execution",
                {"command": command, "base_cmd": base_cmd, "user_id": user_id}
            )
            return False
            
        # Check for restricted commands
        if base_cmd in self._restricted_commands:
            # Check if user has permission to run restricted commands
            if not self._has_permission(user_id, "restricted_commands"):
                self._event_log.add(
                    "security.command.restricted",
                    "Blocked restricted command execution",
                    {"command": command, "base_cmd": base_cmd, "user_id": user_id}
                )
                return False
                
        # Check for dangerous patterns
        dangerous_patterns = [
            r"[;&|]{2,}",  # Multiple command separators
            r"`.*`",       # Command substitution
            r"\$\(.+\)",   # Command substitution
            r";\s*rm\s+-rf",  # rm -rf after semicolon
            r"\|\s*rm\s+-rf",  # rm -rf after pipe
            r"&&\s*rm\s+-rf",  # rm -rf after &&
            r"\|\s*(?:sh|bash|python|perl|ruby)",  # Pipe to interpreters
            r";\s*(?:sh|bash|python|perl|ruby)",   # Semicolon followed by interpreters
            r":\(\)\s*\{\s*:\s*\|\s*:&\s*\};:",   # Fork bomb
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command):
                self._event_log.add(
                    "security.command.pattern_blocked",
                    "Blocked command with dangerous pattern",
                    {"command": command, "pattern": pattern, "user_id": user_id}
                )
                return False
                
        # Check for path traversal attempts
        if ".." in command and ("/.." in command or "\\.." in command):
            self._event_log.add(
                "security.command.path_traversal",
                "Blocked command with path traversal",
                {"command": command, "user_id": user_id}
            )
            return False
            
        return True
        
    def validate_file_path(self, path: str, operation: str = "read", user_id: str = "default") -> bool:
        """Validate that a file path is within allowed boundaries."""
        try:
            # Resolve the path
            resolved_path = Path(path).resolve()
            
            # Get the workspace directory from config
            config = self._config_store.get()
            tools_config = config.get("tools", {})
            workspace_dir = Path(tools_config.get("working_directory", ".")).resolve()
            
            # Check if path is within workspace
            try:
                resolved_path.relative_to(workspace_dir)
            except ValueError:
                self._event_log.add(
                    "security.path.outside_workspace",
                    "Blocked file access outside workspace",
                    {"path": path, "resolved_path": str(resolved_path), "workspace": str(workspace_dir), "user_id": user_id}
                )
                return False
                
            # Additional checks based on operation
            if operation == "write":
                # Ensure parent directory exists and is writable
                parent_dir = resolved_path.parent
                if not parent_dir.exists():
                    # Allow creation of subdirectories within workspace
                    try:
                        parent_dir.relative_to(workspace_dir)
                    except ValueError:
                        self._event_log.add(
                            "security.path.write_denied",
                            "Blocked file write outside workspace",
                            {"path": path, "parent_dir": str(parent_dir), "workspace": str(workspace_dir), "user_id": user_id}
                        )
                        return False
                        
            elif operation == "execute":
                # Check if file is executable
                if not os.access(resolved_path, os.X_OK):
                    self._event_log.add(
                        "security.path.not_executable",
                        "Blocked execution of non-executable file",
                        {"path": path, "user_id": user_id}
                    )
                    return False
                    
            return True
        except Exception as e:
            self._event_log.add(
                "security.path.validation_error",
                "Error validating file path",
                {"path": path, "error": str(e), "user_id": user_id}
            )
            return False
            
    def sanitize_input(self, text: str, max_length: int = 10000, user_id: str = "default") -> str:
        """Sanitize user input to prevent injection attacks."""
        original_length = len(text)
        if original_length > max_length:
            self._event_log.add(
                "security.input.truncated",
                "Truncated overly long input",
                {"original_length": original_length, "truncated_length": max_length, "user_id": user_id}
            )
            text = text[:max_length]
            
        # Remove null bytes
        if '\x00' in text:
            self._event_log.add(
                "security.input.null_bytes_removed",
                "Removed null bytes from input",
                {"user_id": user_id}
            )
            text = text.replace('\x00', '')
        
        # Normalize whitespace but preserve single spaces
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\s*\n\s*', '\n', text)
        
        # Remove dangerous unicode characters
        dangerous_unicode = [
            '\u202e',  # RTL override
            '\u202d',  # LTR override
            '\u202c',  # Pop directional formatting
            '\u200e',  # LTR mark
            '\u200f',  # RTL mark
        ]
        for char in dangerous_unicode:
            if char in text:
                self._event_log.add(
                    "security.input.unicode_filtered",
                    "Filtered dangerous unicode characters",
                    {"character": repr(char), "user_id": user_id}
                )
                text = text.replace(char, '')
        
        return text.strip()
        
    def _has_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has specific permission."""
        # In a full implementation, this would check user roles/permissions
        # For now, we'll use a simple approach based on config
        config = self._config_store.get()
        security_config = config.get("security", {})
        admin_users = security_config.get("admin_users", [])
        return user_id in admin_users


class PermissionManager:
    """Manages permissions and access controls for MiniClaw operations."""
    
    def __init__(self, config_store: ConfigStore, event_log: EventLog) -> None:
        self._config_store = config_store
        self._event_log = event_log
        self._permissions_cache: Dict[str, bool] = {}
        self._cache_timestamps: Dict[str, float] = {}
        
    def check_tool_permission(self, tool_name: str, user_id: str = "default", context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if a user has permission to execute a specific tool."""
        cache_key = f"{user_id}:{tool_name}"
        current_time = time.time()
        
        # Check cache (5 minute TTL)
        if cache_key in self._permissions_cache and current_time - self._cache_timestamps.get(cache_key, 0) < 300:
            return self._permissions_cache[cache_key]
            
        config = self._config_store.get()
        tools_config = config.get("tools", {})
        
        # Global tools enable/disable
        if not tools_config.get("enabled", True):
            self._cache_permission(cache_key, False, current_time)
            return False
            
        # Admin users have full access
        security_config = config.get("security", {})
        admin_users = security_config.get("admin_users", [])
        if user_id in admin_users:
            self._cache_permission(cache_key, True, current_time)
            return True
            
        # Check user-specific tool permissions
        user_permissions = tools_config.get("user_permissions", {}).get(user_id, {})
        if user_permissions:
            # Check if user has explicit permission for this tool
            tool_perm = user_permissions.get(tool_name)
            if tool_perm is not None:
                self._cache_permission(cache_key, bool(tool_perm), current_time)
                return bool(tool_perm)
                
        # Check group permissions
        user_groups = self._get_user_groups(user_id)
        for group in user_groups:
            group_permissions = tools_config.get("group_permissions", {}).get(group, {})
            tool_perm = group_permissions.get(tool_name)
            if tool_perm is not None:
                self._cache_permission(cache_key, bool(tool_perm), current_time)
                return bool(tool_perm)
                
        # Check specific tool permissions
        tool_permissions = tools_config.get("permissions", {})
        if tool_permissions:
            # Check if tool has specific permission settings
            tool_perm = tool_permissions.get(tool_name)
            if tool_perm is not None:
                # If explicitly set, check user permissions
                if isinstance(tool_perm, dict):
                    allowed_users = tool_perm.get("allowed_users", [])
                    allowed_groups = tool_perm.get("allowed_groups", [])
                    if allowed_users and user_id not in allowed_users:
                        # Check if user is in allowed groups
                        if not any(group in allowed_groups for group in user_groups):
                            self._cache_permission(cache_key, False, current_time)
                            return False
                elif not tool_perm:  # Explicitly disabled
                    self._cache_permission(cache_key, False, current_time)
                    return False
                    
        # Check feature-specific permissions
        feature_map = {
            "run_command": "allow_shell",
            "list_dir": "allow_filesystem",
            "read_file": "allow_filesystem",
            "write_file": "allow_filesystem",
            "fetch_url": "allow_network",
            "browser_extract": "allow_browser",
        }
        
        feature_flag = feature_map.get(tool_name)
        if feature_flag:
            result = bool(tools_config.get(feature_flag, True))
            self._cache_permission(cache_key, result, current_time)
            return result
            
        # Default to allowing if no specific rules
        self._cache_permission(cache_key, True, current_time)
        return True
        
    def request_permission(self, tool_name: str, reason: str, user_id: str = "default", timeout: int = 300) -> bool:
        """Request permission for a sensitive operation."""
        self._event_log.add(
            "security.permission.requested",
            "Permission requested for tool execution",
            {"tool": tool_name, "reason": reason, "user_id": user_id}
        )
        # In a full implementation, this would trigger user approval flow
        # For now, we'll check if auto-approval is enabled for this user/tool
        config = self._config_store.get()
        auto_approvals = config.get("security", {}).get("auto_approvals", {})
        user_auto_approvals = auto_approvals.get(user_id, [])
        
        if tool_name in user_auto_approvals:
            self._event_log.add(
                "security.permission.auto_approved",
                "Permission auto-approved",
                {"tool": tool_name, "user_id": user_id}
            )
            return True
            
        # Default deny for sensitive operations
        sensitive_tools = ["run_command", "write_file"]
        if tool_name in sensitive_tools:
            self._event_log.add(
                "security.permission.denied",
                "Permission denied for sensitive tool",
                {"tool": tool_name, "user_id": user_id}
            )
            return False
            
        # Default allow for non-sensitive operations
        return True
        
    def _get_user_groups(self, user_id: str) -> List[str]:
        """Get groups for a user."""
        config = self._config_store.get()
        security_config = config.get("security", {})
        user_groups = security_config.get("user_groups", {})
        return user_groups.get(user_id, [])
        
    def _cache_permission(self, key: str, value: bool, timestamp: float) -> None:
        """Cache permission result."""
        self._permissions_cache[key] = value
        self._cache_timestamps[key] = timestamp


class RateLimiter:
    """Rate limiting for API requests and tool executions."""
    
    def __init__(self, config_store: ConfigStore, event_log: EventLog) -> None:
        self._config_store = config_store
        self._event_log = event_log
        self._request_counts: Dict[str, List[float]] = {}  # user_id -> timestamps
        self._ip_counts: Dict[str, List[float]] = {}  # ip_address -> timestamps
        
    def check_rate_limit(self, user_id: str = "default", ip_address: str = "", limit: int = 100, window: int = 60) -> bool:
        """Check if user has exceeded rate limit."""
        current_time = time.time()
        cutoff_time = current_time - window
        
        # Check user-based rate limiting
        if user_id != "default":
            # Clean up old entries and get current count
            timestamps = self._request_counts.get(user_id, [])
            recent_timestamps = [t for t in timestamps if t > cutoff_time]
            self._request_counts[user_id] = recent_timestamps
            
            # Check if limit exceeded
            if len(recent_timestamps) >= limit:
                self._event_log.add(
                    "security.rate_limit.exceeded",
                    "User rate limit exceeded",
                    {"user_id": user_id, "count": len(recent_timestamps), "limit": limit, "window": window}
                )
                return False
                
            # Add current request
            self._request_counts[user_id].append(current_time)
        
        # Check IP-based rate limiting
        if ip_address:
            # Clean up old entries and get current count
            timestamps = self._ip_counts.get(ip_address, [])
            recent_timestamps = [t for t in timestamps if t > cutoff_time]
            self._ip_counts[ip_address] = recent_timestamps
            
            # Get IP rate limit config
            config = self._config_store.get()
            security_config = config.get("security", {})
            ip_limit = security_config.get("ip_rate_limit", 20)  # Lower limit for IPs
            
            # Check if limit exceeded
            if len(recent_timestamps) >= ip_limit:
                self._event_log.add(
                    "security.rate_limit.ip_exceeded",
                    "IP rate limit exceeded",
                    {"ip_address": ip_address, "count": len(recent_timestamps), "limit": ip_limit, "window": window}
                )
                return False
                
            # Add current request
            self._ip_counts[ip_address].append(current_time)
            
        return True


class ContentFilter:
    """Filters content for sensitive information and inappropriate content."""
    
    def __init__(self, config_store: ConfigStore, event_log: EventLog) -> None:
        self._config_store = config_store
        self._event_log = event_log
        self._sensitive_patterns = [
            r"\b[A-Za-z0-9+/]{40,}\b",  # Potential API keys
            r"\b[A-Fa-f0-9]{32}\b",     # MD5 hashes
            r"\b[A-Fa-f0-9]{40}\b",     # SHA1 hashes
            r"\b[A-Fa-f0-9]{64}\b",     # SHA256 hashes
            r"\b\d{3}-\d{2}-\d{4}\b",   # SSN pattern
            r"\b(?:\d{4}[-\s]?){3}\d{4}\b",  # Credit card pattern
        ]
        
    def filter_output(self, content: str, user_id: str = "default") -> str:
        """Filter sensitive information from output."""
        filtered_content = content
        redacted_count = 0
        
        for pattern in self._sensitive_patterns:
            matches = re.findall(pattern, filtered_content)
            for match in matches:
                # Only redact if it looks like a real secret (not random text)
                if self._looks_like_secret(match):
                    filtered_content = filtered_content.replace(match, "[REDACTED]")
                    redacted_count += 1
                    
        if redacted_count > 0:
            self._event_log.add(
                "security.content.filtered",
                "Redacted sensitive information from output",
                {"redacted_count": redacted_count, "user_id": user_id}
            )
            
        return filtered_content
        
    def _looks_like_secret(self, text: str) -> bool:
        """Determine if text looks like a secret."""
        # Check entropy - high entropy suggests random data (like keys)
        if len(text) > 10:
            entropy = self._calculate_entropy(text)
            if entropy > 3.0:  # Threshold for high entropy
                return True
                
        # Check for common secret patterns
        if re.match(r"^[A-Za-z0-9_+=/-]+$", text) and len(text) > 20:
            return True
            
        return False
        
    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of text."""
        if not text:
            return 0.0
            
        # Count frequency of each character
        freq = {}
        for char in text:
            freq[char] = freq.get(char, 0) + 1
            
        # Calculate entropy
        entropy = 0.0
        text_len = len(text)
        for count in freq.values():
            probability = count / text_len
            if probability > 0:
                entropy -= probability * math.log2(probability)
            
        return entropy


def create_security_managers(config_store: ConfigStore, event_log: EventLog) -> Dict[str, Any]:
    """Factory function to create all security managers."""
    return {
        "sandbox": SandboxManager(config_store, event_log),
        "permissions": PermissionManager(config_store, event_log),
        "rate_limiter": RateLimiter(config_store, event_log),
        "content_filter": ContentFilter(config_store, event_log),
    }