"""Enhanced interactive setup wizard for MiniClaw with KeyDB installation and navigation."""
from __future__ import annotations
import json
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict
from ..cli.cli_utils import CLIExperience, CLIStyle, CLINavigator
from ..core.constants import CONFIG_PATH, WORKSPACE_DIR
from ..core.util import LOGGER


class EnhancedSetupWizard:
    """Enhanced guided setup wizard for MiniClaw with interactive navigation."""

    def __init__(self) -> None:
        self.workspace = WORKSPACE_DIR
        self.config_path = CONFIG_PATH
        self.state: Dict[str, Any] = {}
        self.current_step = 0
        self.cli = CLIExperience("MiniClaw")
        self.style = CLIStyle()
        self.navigator = CLINavigator()
        self.steps = [
            "Welcome",
            "Prerequisites Check",
            "Workspace Setup",
            "Model Provider Configuration",
            "KeyDB Installation",
            "Telegram Configuration",
            "Review & Confirm",
            "Installation"
        ]

    def run(self) -> bool:
        """Run the enhanced setup wizard with interactive navigation."""
        try:
            self.cli.welcome("MiniClaw Enhanced Setup Wizard", "Step-by-step installation with KeyDB support")
            while self.current_step < len(self.steps):
                step_name = self.steps[self.current_step]
                print(f"\n{self.style.step(step_name, step_num=self.current_step + 1, total_steps=len(self.steps))}")
                if step_name == "Welcome":
                    if not self._show_welcome():
                        return False
                elif step_name == "Prerequisites Check":
                    if not self._check_prerequisites_step():
                        return False
                elif step_name == "Workspace Setup":
                    if not self._workspace_setup_step():
                        return False
                elif step_name == "Model Provider Configuration":
                    if not self._model_provider_step():
                        return False
                elif step_name == "KeyDB Installation":
                    if not self._keydb_installation_step():
                        return False
                elif step_name == "Telegram Configuration":
                    if not self._telegram_configuration_step():
                        return False
                elif step_name == "Review & Confirm":
                    if not self._review_confirm_step():
                        return False
                elif step_name == "Installation":
                    if not self._installation_step():
                        return False
                # Move to next step or handle navigation
                nav_choice = self._navigation_menu()
                if nav_choice == "next":
                    self.current_step += 1
                elif nav_choice == "back":
                    self.current_step = max(0, self.current_step - 1)
                elif nav_choice == "quit":
                    return False
                elif nav_choice.startswith("goto_"):
                    step_index = int(nav_choice.split("_")[1])
                    self.current_step = step_index
            self.cli.goodbye("Setup completed successfully!")
            self._show_completion_message()
            return True
        except Exception as e:
            print(f"\n{self.style.error(f'Setup failed: {e}')}")
            LOGGER.exception("Enhanced setup wizard failed")
            return False

    def _navigation_menu(self) -> str:
        """Show navigation menu and return user choice."""
        print("\n--- Navigation ---")
        print("1. Continue to next step")
        print("2. Go back to previous step")
        print("3. Jump to specific step")
        # Show available steps for jumping
        print("\nAvailable steps:")
        for i, step in enumerate(self.steps):
            marker = "→" if i == self.current_step else " "
            current = "(current)" if i == self.current_step else ""
            print(f"   {marker} {i + 1}. {step} {current}")
        print("0. Quit setup")
        while True:
            try:
                choice = input("\nEnter your choice (0-3): ").strip()
                if choice == "0":
                    return "quit"
                elif choice == "1":
                    return "next"
                elif choice == "2":
                    return "back"
                elif choice == "3":
                    step_choice = input("Enter step number to jump to (1-{}): ".format(len(self.steps))).strip()
                    step_index = int(step_choice) - 1
                    if 0 <= step_index < len(self.steps):
                        return f"goto_{step_index}"
                    else:
                        print("Invalid step number.")
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Invalid choice. Please try again.")

    def _show_welcome(self) -> bool:
        """Show welcome screen."""
        print(f"""
{self.style.info("Welcome to the MiniClaw Enhanced Setup Wizard!")}
This wizard will guide you through setting up MiniClaw with:
{self.style.list_item("AI model provider configuration")}
{self.style.list_item("KeyDB for job execution (if needed)")}
{self.style.list_item("Telegram bot integration (optional)")}
{self.style.list_item("Default skills and memory files")}
{self.style.dim("You can navigate between steps using the menu at the end of each step.")}
""")
        ready = self.navigator.get_input("Press Enter to begin setup, or 'q' to quit").strip().lower()
        return ready != 'q'

    def _check_prerequisites_step(self) -> bool:
        """Check system prerequisites."""
        print(f"{self.style.sub_section('Checking system prerequisites...')}")
        # Check Python version
        if sys.version_info < (3, 9):
            print(self.style.error("Python 3.9 or higher is required"))
            return False
        print(self.style.success(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"))
        # Check for package managers
        has_uv = shutil.which("uv") is not None
        has_pip = shutil.which("pip") is not None
        if not has_uv and not has_pip:
            print(self.style.error("Either 'uv' or 'pip' is required for package management"))
            return False
        package_manager = "uv" if has_uv else "pip"
        print(self.style.success(f"Package manager: {package_manager}"))
        # Store in state
        self.state["has_uv"] = has_uv
        self.state["has_pip"] = has_pip
        return True

    def _workspace_setup_step(self) -> bool:
        """Set up workspace directory."""
        print(f"{self.style.sub_section('Workspace Setup')}")
        print(f"Default workspace location: {self.style.highlight(str(self.workspace))}")
        # Allow user to customize workspace location
        custom_path = self.navigator.get_input("\nEnter custom workspace path (or press Enter to use default)").strip()
        if custom_path:
            try:
                custom_workspace = Path(custom_path).expanduser().resolve()
                self.workspace = custom_workspace
                self.state["custom_workspace"] = str(custom_workspace)
                print(self.style.success(f"Using custom workspace: {custom_workspace}"))
            except Exception as e:
                print(self.style.error(f"Invalid path: {e}"))
                return False
        # Show what will be created
        directories = [
            self.workspace,
            self.workspace / "memory",
            self.workspace / "skills",
            self.workspace / "plugins",
            self.workspace / "jobs",
            self.workspace / "generated_scripts"
        ]
        print(f"\n{self.style.info('The following directories will be created:')}")
        for directory in directories:
            print(f"   {self.style.list_item(str(directory))}")
        confirm = self.navigator.confirm("\nContinue with workspace setup?", default=True)
        if not confirm:
            return False
        self.state["workspace"] = str(self.workspace)
        return True

    def _model_provider_step(self) -> bool:
        """Configure model provider."""
        print("\n🤖 AI Model Provider Configuration")
        print("Choose your preferred AI model provider:")
        providers = [
            {
                "id": "ollama_local",
                "name": "Ollama (Local)",
                "description": "Run models locally on your machine",
                "type": "ollama",
                "needs_install": True,
                "install_instructions": "Visit https://ollama.com and follow installation instructions"
            },
            {
                "id": "openai_api",
                "name": "OpenAI API",
                "description": "Use OpenAI's GPT models (requires API key)",
                "type": "openai_compatible",
                "needs_install": False
            },
            {
                "id": "openrouter",
                "name": "OpenRouter",
                "description": "Access to many models through one API (requires API key)",
                "type": "openrouter",
                "needs_install": False
            },
            {
                "id": "openapi_compatible",
                "name": "OpenAPI Compatible",
                "description": "Generic OpenAPI compatible provider (requires base URL and API key)",
                "type": "openai_compatible",
                "needs_install": False
            }
        ]
        print("\nAvailable providers:")
        for i, provider in enumerate(providers, 1):
            print(f"   {i}. {provider['name']} - {provider['description']}")
            if provider.get("needs_install"):
                print(f"      ⚠️  {provider['install_instructions']}")
        while True:
            try:
                choice = input(f"\nSelect provider (1-{len(providers)}): ").strip()
                if choice.lower() == 'b':
                    return False  # Go back
                index = int(choice) - 1
                if 0 <= index < len(providers):
                    selected = providers[index]
                    self.state["provider"] = selected
                    break
                print("Invalid choice. Please try again.")
            except (ValueError, IndexError):
                print("Invalid choice. Please try again.")
        # Configure specific provider settings
        if selected["id"] == "ollama_local":
            return self._configure_ollama_provider()
        elif selected["id"] == "openai_api":
            return self._configure_openai_provider()
        elif selected["id"] == "openrouter":
            return self._configure_openrouter_provider()
        elif selected["id"] == "openapi_compatible":
            return self._configure_openapi_compatible_provider()
        return False

    def _configure_ollama_provider(self) -> bool:
        """Configure Ollama provider."""
        print("\n🔧 Configuring Ollama...")
        # Check if Ollama is installed and running
        try:
            result = subprocess.run(["ollama", "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("✅ Ollama is installed")
                self.state["ollama_installed"] = True
            else:
                print("⚠️  Ollama not found or not running")
                install_now = input("Would you like to install Ollama now? (y/N): ").strip().lower()
                if install_now == 'y':
                    self._install_ollama()
                else:
                    print("   Please install Ollama from https://ollama.com")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("⚠️  Ollama not found")
            install_now = input("Would you like to install Ollama now? (y/N): ").strip().lower()
            if install_now == 'y':
                self._install_ollama()
            else:
                print("   Please install Ollama from https://ollama.com")
        # Pull a default model
        default_model = "qwen3"
        print(f"\n📥 Pulling default model: {default_model}")
        try:
            subprocess.run(["ollama", "pull", default_model], check=True, timeout=300)
            print("✅ Model pulled successfully")
            self.state["ollama_model"] = default_model
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            print("⚠️  Failed to pull model. You can do this later with: ollama pull qwen3")
            self.state["ollama_model"] = default_model
        self.state["provider_config"] = {
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
        return True

    def _install_ollama(self) -> bool:
        """Install Ollama based on OS."""
        system = platform.system().lower()
        print(f"Installing Ollama for {system}...")
        try:
            if system == "darwin":  # macOS
                subprocess.run(["brew", "install", "ollama"], check=True)
            elif system == "linux":
                # Try curl installation
                subprocess.run(["curl", "-fsSL", "https://ollama.com/install.sh", "|", "sh"], shell=True, check=True)
            else:
                print(f"Manual installation required for {system}")
                print("Please visit https://ollama.com and follow installation instructions")
                input("Press Enter after installing Ollama...")
                return True
            print("✅ Ollama installed successfully")
            print("Starting Ollama service...")
            subprocess.Popen(["ollama", "serve"])
            time.sleep(3)  # Give it time to start
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install Ollama automatically")
            print("Please visit https://ollama.com and follow installation instructions")
            input("Press Enter after installing Ollama...")
            return True
        except Exception as e:
            print(f"❌ Installation error: {e}")
            print("Please visit https://ollama.com and follow installation instructions")
            input("Press Enter after installing Ollama...")
            return True

    def _configure_openai_provider(self) -> bool:
        """Configure OpenAI provider."""
        print("\n🔑 Configuring OpenAI API...")
        api_key = input("Enter your OpenAI API key: ").strip()
        if not api_key:
            print("❌ API key is required")
            return False
        model = input("Enter model name (default: gpt-4o-mini): ").strip() or "gpt-4o-mini"
        self.state["provider_config"] = {
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
        return True

    def _configure_openapi_compatible_provider(self) -> bool:
        """Configure generic OpenAPI compatible provider."""
        print("\n🔑 Configuring OpenAPI Compatible Provider...")
        base_url = input("Enter the base URL for your OpenAPI compatible provider: ").strip()
        if not base_url:
            print("❌ Base URL is required")
            return False
        # Ensure the URL ends with /v1 for OpenAI compatible APIs
        if not base_url.endswith("/v1"):
            if base_url.endswith("/"):
                base_url += "v1"
            else:
                base_url += "/v1"

        api_key = input("Enter your API key (optional, press Enter to skip): ").strip()

        model = input("Enter model name (required): ").strip()
        if not model:
            print("❌ Model name is required")
            return False

        provider_id = input("Enter provider ID (default: openapi_default): ").strip() or "openapi_default"
        provider_name = input("Enter provider name (default: OpenAPI Compatible): ").strip() or "OpenAPI Compatible"

        self.state["provider_config"] = {
            "id": provider_id,
            "name": provider_name,
            "type": "openai_compatible",
            "enabled": True,
            "base_url": base_url,
            "api_key": api_key,
            "model": model,
            "temperature": 0.2,
            "timeout_seconds": 300,
            "verify_tls": True,
            "system_prompt_override": "",
        }

        return True

    def _configure_openrouter_provider(self) -> bool:
        """Configure OpenRouter provider."""
        print("\n🔑 Configuring OpenRouter...")
        api_key = input("Enter your OpenRouter API key: ").strip()
        if not api_key:
            print("❌ API key is required")
            return False
        model = input("Enter model name (default: openai/gpt-4o-mini): ").strip() or "openai/gpt-4o-mini"
        self.state["provider_config"] = {
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
        return True

    def _keydb_installation_step(self) -> bool:
        """Install and configure KeyDB."""
        print("\n🔑 KeyDB Installation")
        print("KeyDB is used for job execution in MiniClaw.")
        # Check if KeyDB/Redis is already installed
        has_keydb = shutil.which("keydb-server") is not None
        has_redis = shutil.which("redis-server") is not None
        if has_keydb or has_redis:
            db_type = "KeyDB" if has_keydb else "Redis"
            print(f"✅ {db_type} is already installed")
            self.state["keydb_installed"] = True
            self.state["keydb_type"] = "keydb" if has_keydb else "redis"
            # Ask if they want to use existing installation
            use_existing = input(f"Do you want to use the existing {db_type} installation? (Y/n): ").strip().lower()
            if use_existing != 'n':
                return True
        # Ask if they want to install KeyDB
        install_keydb = input("Would you like to install KeyDB now? (Y/n): ").strip().lower()
        if install_keydb == 'n':
            print("Skipping KeyDB installation. You can install it later manually.")
            self.state["skip_keydb"] = True
            return True
        # Install KeyDB
        print("Installing KeyDB...")
        if not self._install_keydb():
            print("❌ KeyDB installation failed")
            skip = input("Continue without KeyDB? (y/N): ").strip().lower()
            if skip != 'y':
                return False
            self.state["skip_keydb"] = True
            return True
        self.state["keydb_installed"] = True
        self.state["keydb_type"] = "keydb"
        return True

    def _install_keydb(self) -> bool:
        """Install KeyDB based on OS."""
        system = platform.system().lower()
        print(f"Installing KeyDB for {system}...")
        try:
            if system == "linux":
                # Try to install via package manager
                if shutil.which("apt"):
                    # Ubuntu/Debian
                    subprocess.run([
                        "wget", "-O", "keydb.deb",
                        "https://download.keydb.dev/keydb-6.3.4-ubuntu20.04-amd64.deb"
                    ], check=True)
                    subprocess.run(["sudo", "dpkg", "-i", "keydb.deb"], check=True)
                elif shutil.which("yum"):
                    # CentOS/RHEL
                    print("Please install KeyDB manually on CentOS/RHEL")
                    print("Visit https://docs.keydb.dev/docs/install/")
                    input("Press Enter after installing KeyDB...")
                    return True
                else:
                    print("Unsupported Linux distribution for automatic KeyDB installation")
                    print("Visit https://docs.keydb.dev/docs/install/")
                    input("Press Enter after installing KeyDB...")
                    return True
            else:
                print(f"Manual installation required for {system}")
                print("Please visit https://docs.keydb.dev/docs/install/")
                input("Press Enter after installing KeyDB...")
                return True
            print("✅ KeyDB installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install KeyDB: {e}")
            print("Please visit https://docs.keydb.dev/docs/install/")
            input("Press Enter after installing KeyDB...")
            return True
        except Exception as e:
            print(f"❌ Installation error: {e}")
            print("Please visit https://docs.keydb.dev/docs/install/")
            input("Press Enter after installing KeyDB...")
            return True

    def _telegram_configuration_step(self) -> bool:
        """Configure Telegram integration."""
        print("\n📱 Telegram Bot Configuration (Optional)")
        print("You can create a Telegram bot to interact with MiniClaw.")
        print("Visit https://core.telegram.org/bots#botfather to create a bot.")
        configure = input("\nDo you want to configure Telegram now? (y/N): ").strip().lower()
        if configure not in ["y", "yes"]:
            self.state["telegram_config"] = None
            return True
        bot_token = input("Enter your Telegram bot token: ").strip()
        if not bot_token:
            print("   Skipping Telegram configuration")
            self.state["telegram_config"] = None
            return True
        self.state["telegram_config"] = {
            "enabled": True,
            "bot_token": bot_token,
            "allowed_chat_ids": [],
            "binding_mode": "single",
            "poll_interval_seconds": 2,
            "pairing_required": True,
            "pairing_code_ttl_seconds": 600,
            "progress_update_seconds": 12,
        }
        return True

    def _review_confirm_step(self) -> bool:
        """Review and confirm configuration."""
        print("\n📋 Review Configuration")
        print("Please review your settings before proceeding with installation.")
        # Display configuration
        print("\n📁 Workspace:")
        print(f"   Location: {self.state.get('custom_workspace', str(WORKSPACE_DIR))}")
        print("\n🤖 AI Model Provider:")
        provider = self.state.get("provider", {})
        print(f"   Type: {provider.get('name', 'Not configured')}")
        if "provider_config" in self.state:
            config = self.state["provider_config"]
            print(f"   Model: {config.get('model', 'N/A')}")
            if config.get("api_key"):
                print(f"   API Key: ***{config['api_key'][-4:] if len(config['api_key']) > 4 else '***'}")
        print("\n🔑 KeyDB:")
        if self.state.get("skip_keydb"):
            print("   Status: Skipped")
        elif self.state.get("keydb_installed"):
            print(f"   Status: Installed ({self.state.get('keydb_type', 'keydb')})")
        else:
            print("   Status: Not installed")
        print("\n📱 Telegram:")
        if self.state.get("telegram_config"):
            print("   Status: Configured")
        else:
            print("   Status: Not configured (optional)")
        # Confirm
        confirm = input("\nProceed with installation? (Y/n): ").strip().lower()
        return confirm != 'n'

    def _installation_step(self) -> bool:
        """Perform the actual installation."""
        print("\n🚀 Installing MiniClaw...")
        try:
            # Create workspace directories
            self._create_workspace_directories()
            # Install dependencies if needed
            self._install_dependencies()
            # Create configuration
            self._create_configuration()
            # Create default files
            self._create_default_files()
            # Start KeyDB if installed
            if self.state.get("keydb_installed"):
                self._start_keydb_service()
            return True
        except Exception as e:
            print(f"❌ Installation failed: {e}")
            LOGGER.exception("Installation failed")
            return False

    def _create_workspace_directories(self) -> None:
        """Create workspace directories."""
        print("📁 Creating workspace directories...")
        directories = [
            self.workspace,
            self.workspace / "memory",
            self.workspace / "skills",
            self.workspace / "plugins",
            self.workspace / "jobs",
            self.workspace / "generated_scripts"
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"   ✅ Created {directory}")

    def _install_dependencies(self) -> None:
        """Install required dependencies."""
        print("📦 Installing dependencies...")
        # Determine package manager
        package_manager = "uv" if self.state.get("has_uv") else "pip"
        # Install KeyDB Python client if KeyDB is being used
        if self.state.get("keydb_installed"):
            try:
                subprocess.run([package_manager, "install", "redis"], check=True)
                print("   ✅ Installed Redis client (for KeyDB compatibility)")
            except subprocess.CalledProcessError:
                print("   ⚠️  Failed to install Redis client")

    def _create_configuration(self) -> None:
        """Create configuration file."""
        print("⚙️  Creating configuration...")
        # Prepare provider config
        provider_config = self.state.get("provider_config", {})
        telegram_config = self.state.get("telegram_config")
        config = {
            "server": {
                "host": "127.0.0.1",
                "port": 8787,
            },
            "providers": {
                "default_provider_id": provider_config.get("id", "ollama_default"),
                "items": [provider_config] if provider_config else [],
            },
            "telegram": telegram_config or {
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
                "active_channel": "telegram" if telegram_config else "web",
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
        self.config_path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("   ✅ Configuration created")

    def _create_default_files(self) -> None:
        """Create default memory and skill files."""
        print("📄 Creating default files...")
        # Memory files
        memory_dir = self.workspace / "memory"
        memory_files = {
            "soul.md": (
                "# Soul\n\n"
                "Core stance:\n"
                "- Be clear, concrete, and practical.\n"
                "- Prefer explicit tradeoffs over vague advice.\n"
                "- Keep actions observable.\n"
            ),
            "user.md": (
                "# User Profile\n\n"
                "- Preferred style: direct, low fluff.\n"
                "- Update this file when stable user preferences become clear.\n"
            ),
            "project.md": (
                "# Project Context\n\n"
                "- Record durable architecture decisions, constraints, and known risks.\n"
            ),
            "journal.md": (
                "# Journal\n\n"
                "Append short timestamped summaries of important interactions and outcomes.\n"
            ),
        }
        for filename, content in memory_files.items():
            filepath = memory_dir / filename
            if not filepath.exists():
                filepath.write_text(content, encoding="utf-8")
                print(f"   ✅ Created {filename}")
        # Skill files
        skills_dir = self.workspace / "skills"
        skill_files = {
            "issue_triage.md": (
                "# Issue Triage\n\n"
                "keywords: bug,incident,error,regression,fix,root cause\n\n"
                "When queries involve production issues, prioritize:\n"
                "1. observed symptoms,\n"
                "2. likely root causes,\n"
                "3. next diagnostic steps,\n"
                "4. rollback/mitigation options.\n"
            ),
            "research_compare.md": (
                "# Research Compare\n\n"
                "keywords: compare,comparison,tradeoff,options,evaluate\n\n"
                "For comparison requests, provide concise option tables with clear pros/cons and decision criteria.\n"
            ),
            "ship_plan.md": (
                "# Ship Plan\n\n"
                "keywords: plan,roadmap,milestone,deliver,ship,launch\n\n"
                "For execution planning, return phased steps with dependencies, risks, and success checks.\n"
            ),
        }
        for filename, content in skill_files.items():
            filepath = skills_dir / filename
            if not filepath.exists():
                filepath.write_text(content, encoding="utf-8")
                print(f"   ✅ Created {filename}")

    def _start_keydb_service(self) -> None:
        """Start KeyDB service."""
        print("🔑 Starting KeyDB service...")
        try:
            # Try to start KeyDB
            if self.state.get("keydb_type") == "keydb":
                subprocess.Popen(["keydb-server", "--daemonize", "yes"])
            else:
                subprocess.Popen(["redis-server", "--daemonize", "yes"])
            time.sleep(2)  # Give it time to start
            print("   ✅ KeyDB service started")
        except Exception as e:
            print(f"   ⚠️  Failed to start KeyDB service: {e}")
            print("   You may need to start it manually")

    def _show_completion_message(self) -> None:
        """Show completion message with next steps."""
        print(f"\n📁 Workspace: {self.workspace}")
        print(f"⚙️  Config: {self.config_path}")
        if self.state.get("keydb_installed"):
            print("🔑 KeyDB: Installed and running")
        print("\n🚀 Next steps:")
        print("   1. Start the server: miniclaw gateway")
        print("   2. Open http://127.0.0.1:8787 in your browser")
        print("   3. Or chat via CLI: miniclaw agent -m \"Hello!\"")

        # Offer to set up service (skip during testing)
        import os
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            print("\n💡 Optional: Set up MiniClaw as a background service")
            print("   This will make MiniClaw start automatically when your computer boots.")
            try:
                configure_service = input("Do you want to set up the service now? (y/N): ").strip().lower()
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
        if self.state.get("keydb_installed"):
            print("   4. Start Celery worker: celery -A miniclaw.celery_worker worker --loglevel=info")


def run_enhanced_setup_wizard() -> int:
    """Run the enhanced setup wizard and return exit code."""
    wizard = EnhancedSetupWizard()
    success = wizard.run()
    return 0 if success else 1
