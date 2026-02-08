# MiniClaw CLI Styling System

MiniClaw features a comprehensive CLI styling system that provides consistent, colorful, and user-friendly terminal output across all commands. This system enhances usability and provides clear visual feedback.

## Overview

The CLI styling system is implemented in `miniclaw/cli_utils.py` and provides:

- **Consistent Color Scheme**: Unified color palette across all commands
- **Visual Hierarchy**: Clear organization of information with headers, sections, and lists
- **Status Indicators**: Immediate recognition of success, error, warning, and info states
- **Progress Feedback**: Visual indicators for ongoing operations
- **Navigation Aids**: Clear step-by-step guidance

## Color Coding System

### Status Colors

| Status | Color | Icon | Usage |
|--------|-------|------|-------|
| Success | Green | ✓ | Completed operations, positive results |
| Error | Red | ✗ | Failures, exceptions, negative results |
| Warning | Yellow | ⚠ | Cautionary information, non-critical issues |
| Info | Blue | ℹ | General information, neutral status |
| Highlight | Cyan/Purple | N/A | Important values, code snippets |

### Text Styling

| Style | Usage |
|-------|-------|
| **Bold** | Headers, important terms, emphasis |
| *Dim* | Secondary information, metadata |
| `Code` | Commands, file paths, technical terms |
| Underline | URLs, hyperlinks |

## Styling Components

### Headers and Titles

Large, prominent text for major sections:

```
╔════════════════════════════════╗
║    MiniClaw Enhanced Setup     ║
╚════════════════════════════════╝
```

### Section Headers

Organizational dividers for content groups:

```
Skills (3 loaded)
=================
```

### Subsection Headers

Secondary organizational dividers:

```
AI Providers
------------
```

### List Items

Structured content presentation:

```
  • Ollama (Local): Enabled
  • OpenAI API: Disabled
  • OpenRouter: Enabled
```

### Status Indicators

Immediate visual feedback for operations:

```
✓ Health check passed
✗ Configuration validation failed
⚠ Optional component not installed
ℹ Processing request...
```

### Code Snippets

Technical content highlighting:

```
`miniclaw install`
`miniclaw gateway --port 8080`
```

### URLs

Clickable links in terminal:

```
http://127.0.0.1:8787
```

## Progress Indicators

### Progress Bars

Visual feedback for long-running operations:

```
Progress: |███████████████████-----| 80% Complete
```

### Step Tracking

Clear indication of multi-step processes:

```
[1/5] Welcome
[2/5] Prerequisites Check
➤ [3/5] Workspace Setup
  [4/5] Model Provider Configuration
  [5/5] Installation
```

## Implementation Details

### CLIStyle Class

The `CLIStyle` class provides formatting methods:

```python
from miniclaw.cli_utils import CLIStyle

style = CLIStyle()

# Success message
print(style.success("Operation completed successfully"))

# Error message
print(style.error("Failed to connect to server"))

# Warning message
print(style.warning("Configuration file not found"))

# Information message
print(style.info("Processing request..."))

# Header
print(style.header("MiniClaw System Status"))

# Section
print(style.section("AI Providers"))

# Subsection
print(style.sub_section("Available Models"))

# List item
print(style.list_item("qwen3"))

# Code snippet
print(style.code("miniclaw install"))

# URL
print(style.url("http://127.0.0.1:8787"))

# Highlighted text
print(style.highlight("Important value"))

# Dimmed text
print(style.dim("Secondary information"))
```

### CLIColors Class

ANSI color codes for terminal styling:

```python
from miniclaw.cli_utils import CLIColors

colors = CLIColors()

# Basic colors
print(f"{colors.OKGREEN}Success{colors.ENDC}")
print(f"{colors.FAIL}Error{colors.ENDC}")
print(f"{colors.WARNING}Warning{colors.ENDC}")
print(f"{colors.OKBLUE}Info{colors.ENDC}")

# Extended colors
print(f"{colors.PURPLE}Code{colors.ENDC}")
print(f"{colors.CYAN}List item{colors.ENDC}")

# Text formatting
print(f"{colors.BOLD}Bold text{colors.ENDC}")
print(f"{colors.DIM}Dim text{colors.ENDC}")
print(f"{colors.UNDERLINE}Underlined text{colors.ENDC}")
```

### CLIProgressBar Class

Progress bar for long operations:

```python
from miniclaw.cli_utils import CLIProgressBar

# Create progress bar
progress = CLIProgressBar(100, prefix='Progress:', suffix='Complete', length=30)

# Update progress
progress.update(25)  # 25% complete
progress.update(50)  # 50% complete
progress.finish()    # 100% complete
```

### CLINavigator Class

Navigation helpers for interactive processes:

```python
from miniclaw.cli_utils import CLINavigator

navigator = CLINavigator()

# Show menu and get selection
options = ["Option 1", "Option 2", "Option 3"]
choice = navigator.show_menu(options, "Choose an option:")

# Confirmation prompt
confirmed = navigator.confirm("Are you sure?", default=True)

# Input with default value
value = navigator.get_input("Enter value", default="default")
```

## Consistency Guidelines

### Message Formatting

All user-facing messages should follow these patterns:

1. **Success Messages**
   ```
   ✓ Operation completed successfully
   ✓ File saved: config.json
   ```

2. **Error Messages**
   ```
   ✗ Failed to connect to server: Connection refused
   ✗ Invalid configuration: Missing required field
   ```

3. **Warning Messages**
   ```
   ⚠ Optional component not installed
   ⚠ Configuration file not found, using defaults
   ```

4. **Information Messages**
   ```
   ℹ Processing request...
   ℹ Server started on port 8787
   ```

### Data Presentation

Structured data should be presented with clear hierarchy:

```
Runtime Information
===================
Config Path:    /home/user/.miniclaw/miniclaw_config.json
Workspace:      /home/user/.miniclaw

Services Status:
----------------
  Telegram: Enabled
  Jobs:     Enabled

AI Providers:
-------------
  Ollama Default (ollama): Enabled
    Model: qwen3

Loaded Components:
------------------
  Skills:  3
  Plugins: 2
```

### Interactive Elements

Menu-driven interfaces should follow consistent patterns:

```
Choose an option:
  1. Option One
  2. Option Two
  3. Option Three

Enter your choice (1-3): 
```

## Best Practices

### Accessibility

1. **Color Contrast**: Ensure sufficient contrast for readability
2. **Text Alternatives**: Provide text equivalents for color-only information
3. **Screen Reader Compatibility**: Use semantic text structure

### Performance

1. **Minimal Overhead**: Styling should not significantly impact performance
2. **Efficient String Operations**: Use efficient string concatenation
3. **Memory Management**: Avoid excessive string object creation

### Cross-Platform Compatibility

1. **Terminal Support**: Test on various terminal emulators
2. **Color Support Detection**: Gracefully degrade on monochrome terminals
3. **Character Set Compatibility**: Use standard ASCII where possible

## Customization

### Theme System

The styling system can be extended with themes:

```python
class DarkTheme(CLIColors):
    """Dark terminal theme colors."""
    BACKGROUND = '\033[40m'
    TEXT = '\033[37m'

class LightTheme(CLIColors):
    """Light terminal theme colors."""
    BACKGROUND = '\033[47m'
    TEXT = '\033[30m'
```

### Branding

Custom branding can be applied:

```python
class BrandStyle(CLIStyle):
    """Custom branded styling."""
    
    @staticmethod
    def brand_header(text: str) -> str:
        """Brand-specific header styling."""
        return f"{CLIColors.BOLD}{CLIColors.PURPLE}>>> {text} <<<{CLIColors.ENDC}"
```

## Integration Examples

### Command Implementation

Example of integrating styling into a CLI command:

```python
def run_health_check(args):
    """Health check command with styled output."""
    print(style.header("MiniClaw Health Check"))
    
    try:
        result = check_server_health()
        if result.healthy:
            print(style.success("Server is healthy"))
            print(f"  Uptime: {style.highlight(result.uptime)}")
            print(f"  Version: {style.dim(result.version)}")
        else:
            print(style.error("Server health check failed"))
            print(f"  Error: {result.error_message}")
    except Exception as e:
        print(style.error(f"Health check error: {e}"))
        return 1
    
    return 0
```

### Interactive Setup

Example of styled interactive setup:

```python
def interactive_setup():
    """Interactive setup with navigation."""
    cli.welcome("MiniClaw Setup", "Step-by-step configuration")
    
    steps = ["Welcome", "Configuration", "Installation"]
    
    for i, step in enumerate(steps, 1):
        print(style.step(step, step_num=i, total_steps=len(steps)))
        
        if step == "Configuration":
            # Show configuration options
            print(style.sub_section("AI Provider"))
            providers = ["Ollama", "OpenAI", "OpenRouter"]
            choice = navigator.show_menu(providers, "Select provider:")
            
            if choice >= 0:
                print(style.success(f"Selected: {providers[choice]}"))
```

## Testing

The styling system includes comprehensive tests:

```python
def test_cli_styling():
    """Test CLI styling functionality."""
    style = CLIStyle()
    
    # Test all styling methods
    assert "✓" in style.success("test")
    assert "✗" in style.error("test")
    assert "⚠" in style.warning("test")
    assert "ℹ" in style.info("test")
    
    # Test color codes
    colors = CLIColors()
    assert colors.OKGREEN in colors.OKGREEN + "test" + colors.ENDC
```

This comprehensive styling system ensures that MiniClaw provides a professional, consistent, and user-friendly command-line experience across all platforms and terminal environments.