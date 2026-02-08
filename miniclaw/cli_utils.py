"""Unified CLI utilities for consistent styling and user experience."""
from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional


class CLIColors:
    """ANSI color codes for terminal styling."""
    
    # Basic colors
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'
    
    # Extended colors
    PURPLE = '\033[35m'
    CYAN = '\033[36m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[34m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    RED = '\033[31m'
    BOLD_RED = '\033[1;31m'
    BOLD_GREEN = '\033[1;32m'
    BOLD_YELLOW = '\033[1;33m'
    BOLD_BLUE = '\033[1;34m'
    BOLD_PURPLE = '\033[1;35m'
    BOLD_CYAN = '\033[1;36m'
    BOLD_WHITE = '\033[1;37m'


class CLIStyle:
    """Consistent CLI styling and formatting utilities."""
    
    def __init__(self):
        self.colors = CLIColors()
    
    @staticmethod
    def header(text: str) -> str:
        """Format header text."""
        return f"{CLIColors.HEADER}{CLIColors.BOLD}{text}{CLIColors.ENDC}"
    
    @staticmethod
    def success(text: str) -> str:
        """Format success text."""
        return f"{CLIColors.OKGREEN}✓ {text}{CLIColors.ENDC}"
    
    @staticmethod
    def error(text: str) -> str:
        """Format error text."""
        return f"{CLIColors.FAIL}✗ {text}{CLIColors.ENDC}"
    
    @staticmethod
    def warning(text: str) -> str:
        """Format warning text."""
        return f"{CLIColors.WARNING}⚠ {text}{CLIColors.ENDC}"
    
    @staticmethod
    def info(text: str) -> str:
        """Format info text."""
        return f"{CLIColors.OKBLUE}ℹ {text}{CLIColors.ENDC}"
    
    @staticmethod
    def highlight(text: str) -> str:
        """Format highlighted text."""
        return f"{CLIColors.BOLD}{text}{CLIColors.ENDC}"
    
    @staticmethod
    def dim(text: str) -> str:
        """Format dimmed text."""
        return f"{CLIColors.DIM}{text}{CLIColors.ENDC}"
    
    @staticmethod
    def bold(text: str) -> str:
        """Format bold text."""
        return f"{CLIColors.BOLD}{text}{CLIColors.ENDC}"
    
    @staticmethod
    def endc() -> str:
        """End color formatting."""
        return CLIColors.ENDC
    
    @staticmethod
    def step(title: str, description: str = "", step_num: Optional[int] = None, total_steps: Optional[int] = None) -> str:
        """Format a step in the process."""
        if step_num is not None and total_steps is not None:
            step_indicator = f"[{step_num}/{total_steps}] "
        elif step_num is not None:
            step_indicator = f"[{step_num}] "
        else:
            step_indicator = ""
        
        result = f"{CLIColors.BOLD_BLUE}{step_indicator}{title}{CLIColors.ENDC}"
        if description:
            result += f"\n   {description}"
        return result
    
    @staticmethod
    def section(title: str) -> str:
        """Format a section header."""
        return f"\n{CLIColors.BOLD_WHITE}{title}{CLIColors.ENDC}\n{'=' * len(title)}"
    
    @staticmethod
    def sub_section(title: str) -> str:
        """Format a subsection header."""
        return f"\n{CLIColors.BOLD_CYAN}{title}{CLIColors.ENDC}\n{'-' * len(title)}"
    
    @staticmethod
    def list_item(text: str, bullet: str = "•") -> str:
        """Format a list item."""
        return f"  {CLIColors.OKCYAN}{bullet}{CLIColors.ENDC} {text}"
    
    @staticmethod
    def code(text: str) -> str:
        """Format code text."""
        return f"{CLIColors.PURPLE}`{text}`{CLIColors.ENDC}"
    
    @staticmethod
    def url(text: str) -> str:
        """Format URL text."""
        return f"{CLIColors.OKBLUE}{CLIColors.UNDERLINE}{text}{CLIColors.ENDC}"


class CLIProgressBar:
    """Simple progress bar for CLI operations."""
    
    def __init__(self, total: int, prefix: str = '', suffix: str = '', length: int = 30, fill: str = '█'):
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.length = length
        self.fill = fill
        self.current = 0
    
    def update(self, increment: int = 1) -> None:
        """Update progress bar."""
        self.current = min(self.current + increment, self.total)
        self._print_progress()
    
    def finish(self) -> None:
        """Finish progress bar."""
        self.current = self.total
        self._print_progress()
        print()  # New line after completion
    
    def _print_progress(self) -> None:
        """Print the progress bar."""
        percent = f"{100 * (self.current / float(self.total)):.1f}"
        filled_length = int(self.length * self.current // self.total)
        bar = self.fill * filled_length + '-' * (self.length - filled_length)
        
        print(f'\r{self.prefix} |{CLIColors.OKGREEN}{bar}{CLIColors.ENDC}| {percent}% {self.suffix}', end='')
        
        # Print new line on complete
        if self.current == self.total:
            print()


class CLINavigator:
    """Navigation helper for step-by-step CLI processes."""
    
    @staticmethod
    def show_menu(options: List[str], prompt: str = "Choose an option:") -> int:
        """Show a menu and return selected option index."""
        print(f"\n{CLIColors.BOLD_WHITE}{prompt}{CLIColors.ENDC}")
        for i, option in enumerate(options, 1):
            print(f"  {CLIColors.OKCYAN}{i}{CLIColors.ENDC}. {option}")
        
        while True:
            try:
                choice = input(f"\n{CLIColors.BOLD}Enter your choice (1-{len(options)}): {CLIColors.ENDC}").strip()
                if choice.lower() in ['q', 'quit']:
                    return -1
                if choice.lower() in ['b', 'back']:
                    return -2
                
                index = int(choice) - 1
                if 0 <= index < len(options):
                    return index
                else:
                    print(CLIStyle.error(f"Please enter a number between 1 and {len(options)}"))
            except ValueError:
                print(CLIStyle.error("Please enter a valid number"))
    
    @staticmethod
    def confirm(prompt: str, default: bool = True) -> bool:
        """Show confirmation prompt."""
        default_text = "Y/n" if default else "y/N"
        while True:
            response = input(f"{CLIColors.BOLD}{prompt} ({default_text}): {CLIColors.ENDC}").strip().lower()
            if not response:
                return default
            if response in ['y', 'yes']:
                return True
            if response in ['n', 'no']:
                return False
            print(CLIStyle.error("Please enter 'y' or 'n'"))
    
    @staticmethod
    def get_input(prompt: str, default: str = "", required: bool = False) -> str:
        """Get user input with optional default."""
        if default:
            prompt_text = f"{CLIColors.BOLD}{prompt} [{default}]: {CLIColors.ENDC}"
        else:
            prompt_text = f"{CLIColors.BOLD}{prompt}: {CLIColors.ENDC}"
        
        while True:
            value = input(prompt_text).strip()
            if not value and default:
                return default
            if not value and required:
                print(CLIStyle.error("This field is required"))
                continue
            return value


class CLIExperience:
    """Unified CLI experience manager."""
    
    def __init__(self, app_name: str = "MiniClaw") -> None:
        self.app_name = app_name
        self.style = CLIStyle()
        self.colors = CLIColors()
    
    def welcome(self, title: str, subtitle: str = "") -> None:
        """Show welcome message."""
        print(f"{self.colors.BOLD_WHITE}")
        print("╔" + "═" * (len(title) + 2) + "╗")
        print(f"║ {title} ║")
        print("╚" + "═" * (len(title) + 2) + "╝")
        print(f"{self.colors.ENDC}")
        
        if subtitle:
            print(f"{self.colors.OKCYAN}{subtitle}{self.colors.ENDC}")
        print()
    
    def goodbye(self, message: str = "Operation completed successfully!") -> None:
        """Show completion message."""
        print(f"\n{self.style.success(message)}")
        print(f"{self.colors.DIM}Thank you for using {self.app_name}!{self.colors.ENDC}")
    
    def show_steps(self, steps: List[str], current_step: int) -> None:
        """Show progress through steps."""
        print(f"\n{self.colors.BOLD_WHITE}Progress:{self.colors.ENDC}")
        for i, step in enumerate(steps, 1):
            if i < current_step:
                print(f"  {self.colors.OKGREEN}✓{self.colors.ENDC} {step}")
            elif i == current_step:
                print(f"  {self.colors.BOLD_YELLOW}➤{self.colors.ENDC} {self.colors.BOLD}{step}{self.colors.ENDC}")
            else:
                print(f"  {self.colors.DIM}○ {step}{self.colors.ENDC}")
    
    def show_data_table(self, data: Dict[str, Any], title: str = "Configuration") -> None:
        """Show data in a formatted table."""
        print(f"\n{self.style.sub_section(title)}")
        for key, value in data.items():
            if isinstance(value, dict):
                print(f"  {self.colors.BOLD}{key}:{self.colors.ENDC}")
                for sub_key, sub_value in value.items():
                    print(f"    {self.colors.OKCYAN}{sub_key}:{self.colors.ENDC} {sub_value}")
            else:
                print(f"  {self.colors.BOLD}{key}:{self.colors.ENDC} {value}")


# Global instance for easy access
cli_style = CLIStyle()
cli_colors = CLIColors()
cli_experience = CLIExperience()