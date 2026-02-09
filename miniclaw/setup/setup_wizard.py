"""Setup wizard for MiniClaw: guided installation and configuration for non-developers."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from typing import Any, Dict, Optional

from ..core.constants import CONFIG_PATH, WORKSPACE_DIR
from ..core.util import LOGGER


class SetupWizard:
    """Guided setup wizard for MiniClaw."""

    def __init__(self) -> None:
        self.workspace = WORKSPACE_DIR
        self.config_path = CONFIG_PATH

    def run(self) -> bool:
        """Run the setup wizard and return True if successful."""
        try:
            print("=== MiniClaw Setup Wizard ===\n")

            # Check prerequisites
            if not self._check_prerequisites():
                return False

            # Create workspace
            self._create_workspace()

            # Configure model provider
            provider_config = self._configure_model_provider()
            if not provider_config:
                return False

            # Configure Telegram (optional)
            telegram_config = self._configure_telegram()

            # Create default config
            self._create_default_config(provider_config, telegram_config)

            # Create default files
            self._create_default_files()

            print("\n✅ Setup completed successfully!")
            print(f"📁 Workspace: {self.workspace}")
            print(f"⚙️  Config: {self.config_path}")
            print("\n🚀 Next steps:")
            print("   1. Start the server: miniclaw gateway")
            print("   2. Open http://127.0.0.1:8787 in your browser")
            print('   3. Or chat via CLI: miniclaw agent -m "Hello!"')

            # Offer to set up service (skip during testing)
            import os

            if not os.environ.get("PYTEST_CURRENT_TEST"):
                print("\n💡 Optional: Set up MiniClaw as a background service")
                print(
                    "   This will make MiniClaw start automatically when your computer boots."
                )
                try:
                    configure_service = (
                        input("Do you want to set up the service now? (y/N): ")
                        .strip()
                        .lower()
                    )
                    if configure_service in ["y", "yes"]:
                        try:
                            from .init_service import install_service

                            install_service()
                        except ImportError:
                            print("Service setup module not found.")
                        except Exception as e:
                            print(f"Service setup failed: {e}")
                except EOFError:
                    # Handle case where input is not available (e.g., in CI)
                    print("\nSkipping service setup (no input available)")

            return True

        except Exception as e:
            print(f"\n❌ Setup failed: {e}")
            LOGGER.exception("Setup wizard failed")
            return False

    def _check_prerequisites(self) -> bool:
        """Check system prerequisites."""
        print("🔍 Checking prerequisites...")

        # Check Python version
        if sys.version_info < (3, 9):
            print("❌ Python 3.9 or higher is required")
            return False
        print(
            f"✅ Python {sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}"
        )

        # Check for pip or uv
        has_uv = shutil.which("uv") is not None
        has_pip = shutil.which("pip") is not None

        if not has_uv and not has_pip:
            print("❌ Either 'uv' or 'pip' is required for package management")
            return False
        print(f"✅ Package manager: {'uv' if has_uv else 'pip'}")

        return True

    def _create_workspace(self) -> None:
        """Create the workspace directory structure."""
        print(f"\n📁 Creating workspace at {self.workspace}")

        # Create directories
        directories = [
            self.workspace,
            self.workspace / "memory",
            self.workspace / "skills",
            self.workspace / "plugins",
            self.workspace / "jobs",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"   ✅ Created {directory}")

    def _configure_model_provider(self) -> Optional[Dict[str, Any]]:
        """Configure model provider through interactive prompts."""
        print("\n🤖 Configure AI Model Provider")
        print("   MiniClaw needs an AI model provider to work.")

        providers = [
            {
                "id": "ollama_local",
                "name": "Ollama (Local)",
                "description": "Run models locally on your machine",
                "type": "ollama",
                "needs_install": True,
                "install_instructions": "Visit https://ollama.com and follow installation instructions",
            },
            {
                "id": "openai_api",
                "name": "OpenAI API",
                "description": "Use OpenAI's GPT models (requires API key)",
                "type": "openai_compatible",
                "needs_install": False,
            },
            {
                "id": "openrouter",
                "name": "OpenRouter",
                "description": "Access to many models through one API (requires API key)",
                "type": "openrouter",
                "needs_install": False,
            },
        ]

        print("\nAvailable providers:")
        for i, provider in enumerate(providers, 1):
            print(f"   {i}. {provider['name']} - {provider['description']}")
            if provider.get("needs_install"):
                print(f"      ⚠️  {provider['install_instructions']}")

        while True:
            try:
                choice = input(f"\nSelect provider (1-{len(providers)}): ").strip()
                index = int(choice) - 1
                if 0 <= index < len(providers):
                    selected = providers[index]
                    break
                print("Invalid choice. Please try again.")
            except (ValueError, IndexError):
                print("Invalid choice. Please try again.")

        # Configure specific provider settings
        if selected["id"] == "ollama_local":
            return self._configure_ollama()
        elif selected["id"] == "openai_api":
            return self._configure_openai()
        elif selected["id"] == "openrouter":
            return self._configure_openrouter()

        return None

    def _configure_ollama(self) -> Optional[Dict[str, Any]]:
        """Configure Ollama provider."""
        print("\n🔧 Configuring Ollama...")

        # Check if Ollama is installed and running
        try:
            result = subprocess.run(
                ["ollama", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print("✅ Ollama is installed")
            else:
                print("⚠️  Ollama not found or not running")
                print("   Please install Ollama from https://ollama.com and start it")
                input("   Press Enter after installing and starting Ollama...")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("⚠️  Ollama not found")
            print("   Please install Ollama from https://ollama.com")
            input("   Press Enter after installing Ollama...")

        # Pull a default model
        default_model = "qwen3"
        print(f"\n📥 Pulling default model: {default_model}")
        try:
            subprocess.run(["ollama", "pull", default_model], check=True)
            print("✅ Model pulled successfully")
        except subprocess.CalledProcessError:
            print(
                "⚠️  Failed to pull model. You can do this later with: ollama pull qwen3"
            )

        return {
            "id": "ollama_default",
            "name": "Ollama Default",
            "type": "ollama",
            "enabled": True,
            "base_url": "http://localhost:11434",
            "api_key": "",
            "model": default_model,
            "temperature": 0.2,
            "timeout_seconds": 300,
            "verify_tls": True,
            "system_prompt_override": "",
        }

    def _configure_openai(self) -> Optional[Dict[str, Any]]:
        """Configure OpenAI provider."""
        print("\n🔑 Configuring OpenAI API...")

        api_key = input("Enter your OpenAI API key: ").strip()
        if not api_key:
            print("❌ API key is required")
            return None

        model = (
            input("Enter model name (default: gpt-4o-mini): ").strip() or "gpt-4o-mini"
        )

        return {
            "id": "openai_default",
            "name": "OpenAI Default",
            "type": "openai_compatible",
            "enabled": True,
            "base_url": "https://api.openai.com/v1",
            "api_key": api_key,
            "model": model,
            "temperature": 0.2,
            "timeout_seconds": 300,
            "verify_tls": True,
            "system_prompt_override": "",
        }

    def _configure_openrouter(self) -> Optional[Dict[str, Any]]:
        """Configure OpenRouter provider."""
        print("\n🔑 Configuring OpenRouter...")

        api_key = input("Enter your OpenRouter API key: ").strip()
        if not api_key:
            print("❌ API key is required")
            return None

        model = (
            input("Enter model name (default: openai/gpt-4o-mini): ").strip()
            or "openai/gpt-4o-mini"
        )

        return {
            "id": "openrouter_default",
            "name": "OpenRouter Default",
            "type": "openrouter",
            "enabled": True,
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": api_key,
            "model": model,
            "temperature": 0.2,
            "timeout_seconds": 300,
            "verify_tls": True,
            "system_prompt_override": "",
        }

    def _configure_telegram(self) -> Optional[Dict[str, Any]]:
        """Configure Telegram integration (optional)."""
        print("\n📱 Configure Telegram Bot (optional)")
        print("   You can create a Telegram bot to interact with MiniClaw.")
        print("   Visit https://core.telegram.org/bots#botfather to create a bot.")

        configure = (
            input("\nDo you want to configure Telegram now? (y/N): ").strip().lower()
        )
        if configure not in ["y", "yes"]:
            return None

        bot_token = input("Enter your Telegram bot token: ").strip()
        if not bot_token:
            print("   Skipping Telegram configuration")
            return None

        return {
            "enabled": True,
            "bot_token": bot_token,
            "allowed_chat_ids": [],
            "binding_mode": "single",
            "poll_interval_seconds": 2,
            "pairing_required": True,
            "pairing_code_ttl_seconds": 600,
            "progress_update_seconds": 12,
        }

    def _create_default_config(
        self, provider_config: Dict[str, Any], telegram_config: Optional[Dict[str, Any]]
    ) -> None:
        """Create the default configuration file."""
        print(f"\n⚙️  Creating configuration at {self.config_path}")

        # Ensure parent directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        config = {
            "server": {
                "host": "127.0.0.1",
                "port": 8787,
            },
            "providers": {
                "default_provider_id": provider_config["id"],
                "items": [provider_config],
            },
            "telegram": telegram_config
            or {
                "enabled": False,
                "bot_token": "",
                "allowed_chat_ids": [],
                "binding_mode": "single",
                "poll_interval_seconds": 2,
                "pairing_required": True,
                "pairing_code_ttl_seconds": 600,
                "progress_update_seconds": 12,
            },
            "channels": {
                "active_channel": "telegram",
                "telegram": {},
                "whatsapp_wacli": {
                    "enabled": False,
                    "wacli_command": "wacli",
                    "session": "",
                    "allowed_contacts": [],
                    "poll_interval_seconds": 15,
                },
                "email": {
                    "enabled": False,
                    "imap_host": "",
                    "smtp_host": "",
                    "username": "",
                    "password": "",
                    "from_address": "",
                    "allowed_senders": [],
                    "poll_interval_seconds": 60,
                },
            },
            "agent": {
                "name": "MiniClaw",
                "system_prompt_default": (
                    "You are MiniClaw, optimized for smaller models. "
                    "Be explicit about what actions you took, what data you used, and why."
                ),
                "max_history_messages": 12,
                "enabled_skills": [],
                "enabled_plugins": ["trace_tag"],
                "skill_match_min_score": 2,
                "seeded_default_skills": False,
            },
            "memory": {
                "enabled": True,
                "files": ["soul.md", "user.md", "project.md", "journal.md"],
                "max_chars_per_file": 3000,
            },
            "tools": {
                "enabled": True,
                "max_steps": 4,
                "allow_shell": True,
                "allow_filesystem": True,
                "allow_network": True,
                "allow_browser": True,
                "allow_mcp": True,
                "command_timeout_seconds": 25,
                "output_char_limit": 12000,
                "working_directory": str(self.workspace),
            },
            "mcp": {
                "enabled": True,
                "servers": [],
            },
            "monitoring": {
                "max_events": 700,
            },
            "jobs": {
                "enabled": True,
                "jobs": [],
                "seeded_default_jobs": False,
            },
        }

        # Write config file
        self.config_path.write_text(
            json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print("   ✅ Configuration created")

    def _create_default_files(self) -> None:
        """Create default memory and skill files."""
        print("\n📄 Creating default files...")

        # Import constants to access template directories
        from ..core.constants import (
            MEMORY_TEMPLATE_DIR,
            SKILLS_TEMPLATE_DIR,
            PLUGINS_TEMPLATE_DIR,
        )

        # Copy memory files from templates
        memory_dir = self.workspace / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
        if MEMORY_TEMPLATE_DIR.exists():
            for template_file in MEMORY_TEMPLATE_DIR.iterdir():
                if template_file.is_file():
                    dest_file = memory_dir / template_file.name
                    if not dest_file.exists():
                        dest_file.write_text(
                            template_file.read_text(encoding="utf-8"), encoding="utf-8"
                        )
                        print(f"   ✅ Created {template_file.name}")

        # Copy skill files from templates
        skills_dir = self.workspace / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
        if SKILLS_TEMPLATE_DIR.exists():
            for template_file in SKILLS_TEMPLATE_DIR.iterdir():
                if template_file.is_file():
                    dest_file = skills_dir / template_file.name
                    if not dest_file.exists():
                        dest_file.write_text(
                            template_file.read_text(encoding="utf-8"), encoding="utf-8"
                        )
                        print(f"   ✅ Created {template_file.name}")

        # Copy plugin files from templates (optional)
        plugins_dir = self.workspace / "plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
        if PLUGINS_TEMPLATE_DIR.exists():
            for template_file in PLUGINS_TEMPLATE_DIR.iterdir():
                if template_file.is_file():
                    dest_file = plugins_dir / template_file.name
                    if not dest_file.exists():
                        dest_file.write_text(
                            template_file.read_text(encoding="utf-8"), encoding="utf-8"
                        )
                        print(f"   ✅ Created {template_file.name}")


def run_setup_wizard() -> int:
    """Run the setup wizard and return exit code."""
    wizard = SetupWizard()
    success = wizard.run()
    return 0 if success else 1
