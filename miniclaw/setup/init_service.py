"""Service initialization module for MiniClaw."""
import os
import subprocess
import platform
from pathlib import Path


def query_user_for_service_installation():
    """Ask the user if they want to install the service."""
    print("\n" + "="*50)
    print("MiniClaw Service Setup")
    print("="*50)

    while True:
        response = input("Would you like to set up MiniClaw to run as a background service? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' for yes or 'n' for no.")


def install_service():
    """Install the appropriate service based on the operating system."""
    os_type = platform.system().lower()

    if os_type == "linux":
        return install_linux_service()
    elif os_type == "darwin":  # macOS
        return install_macos_service()
    elif os_type == "windows":
        return install_windows_service()
    else:
        print(f"Unsupported operating system for automatic service installation: {os_type}")
        return False


def install_linux_service():
    """Install systemd service on Linux."""
    print("Setting up systemd service for Linux...")

    # Check if we're in a test environment with a special environment variable
    # that indicates we should simulate systemd not being available
    if os.environ.get("MINICLAW_TEST_NO_SYSTEMD") == "1":
        print("systemd not found. Cannot install service automatically.")
        return False

    # Check if systemd is available and functional
    if not os.path.exists("/etc/systemd/system"):
        print("systemd not found. Cannot install service automatically.")
        return False

    # Additional check to ensure systemd is functional
    try:
        # Try to run systemctl to verify systemd is actually available
        subprocess.check_output(["systemctl", "--version"], stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("systemd not found. Cannot install service automatically.")
        return False

    # Try to get the miniclaw executable path
    try:
        miniclaw_path = subprocess.check_output(["which", "miniclaw"], stderr=subprocess.DEVNULL).decode().strip()
    except subprocess.CalledProcessError:
        miniclaw_path = "miniclaw"  # fallback

    # Create service content
    service_content = f"""[Unit]
Description=MiniClaw AI Agent
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'miniclaw')}
Group={os.getenv('USER', 'miniclaw')}
WorkingDirectory={os.getcwd()}
Environment=PATH={os.getenv('PATH', '/usr/local/bin:/usr/bin:/bin')}
ExecStart={miniclaw_path} gateway
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={Path.home()}/.miniclaw

[Install]
WantedBy=multi-user.target
"""

    # Write service file to current directory
    service_file = Path.cwd() / "miniclaw.service"
    try:
        with open(service_file, "w") as f:
            f.write(service_content)

        print(f"Service file created: {service_file}")
        print("To complete installation, run the following commands with sudo:")
        print(f"  sudo cp {service_file} /etc/systemd/system/")
        print("  sudo systemctl daemon-reload")
        print("  sudo systemctl enable miniclaw")
        print("  sudo systemctl start miniclaw")
        return True
    except Exception as e:
        print(f"Error creating service file: {e}")
        return False


def install_macos_service():
    """Install launch daemon on macOS."""
    print("Setting up launch agent for macOS...")

    # Try to get the miniclaw executable path
    try:
        miniclaw_path = subprocess.check_output(["which", "miniclaw"], stderr=subprocess.DEVNULL).decode().strip()
    except subprocess.CalledProcessError:
        miniclaw_path = "miniclaw"  # fallback

    # Create plist content
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.miniclaw.agent</string>

    <key>ProgramArguments</key>
    <array>
        <string>{miniclaw_path}</string>
        <string>gateway</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>WorkingDirectory</key>
    <string>{os.getcwd()}</string>

    <key>StandardOutPath</key>
    <string>{Path.home()}/.miniclaw/logs/miniclaw.out.log</string>

    <key>StandardErrorPath</key>
    <string>{Path.home()}/.miniclaw/logs/miniclaw.err.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{os.getenv('PATH', '/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin')}</string>
    </dict>
</dict>
</plist>
"""

    # Write plist file
    plist_dir = Path.home() / "Library" / "LaunchAgents"
    plist_dir.mkdir(parents=True, exist_ok=True)
    plist_path = plist_dir / "com.miniclaw.agent.plist"

    try:
        with open(plist_path, "w") as f:
            f.write(plist_content)

        print(f"Launch agent plist created: {plist_path}")
        print("To complete installation, run:")
        print(f"  launchctl load {plist_path}")
        print("Or reboot your system for the service to start automatically.")
        return True
    except Exception as e:
        print(f"Error creating plist file: {e}")
        return False


def install_windows_service():
    """Create Windows service installation files."""
    print("Creating Windows service installation files...")

    # Create PowerShell script for service installation
    ps1_content = """# MiniClaw Windows Service Installation Script (PowerShell)

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "This script requires administrator privileges." -ForegroundColor Red
    Write-Host "Please run as Administrator." -ForegroundColor Yellow
    Write-Host "Right-click on PowerShell and select 'Run as administrator'." -ForegroundColor Yellow
    exit 1
}

try {
    # Try to find miniclaw executable
    $miniclawPath = Get-Command "miniclaw" -ErrorAction SilentlyContinue
    if ($miniclawPath) {
        $exePath = $miniclawPath.Source
    } else {
        # Fallback to current directory
        $exePath = Join-Path $PSScriptRoot "miniclaw.exe"
        if (-not (Test-Path $exePath)) {
            Write-Host "Could not find miniclaw executable. Please ensure it's installed and in PATH." `
                -ForegroundColor Red
            exit 1
        }
    }

    # Create the service
    $serviceName = "MiniClaw"
    New-Service -Name $serviceName -BinaryPathName "`"$exePath`" gateway" `
        -DisplayName "MiniClaw AI Agent" -StartupType Automatic

    Write-Host "Service installed successfully." -ForegroundColor Green

    # Start the service
    Write-Host "Starting the service..." -ForegroundColor Yellow
    Start-Service -Name $serviceName

    if ((Get-Service -Name $serviceName).Status -eq "Running") {
        Write-Host "Service started successfully." -ForegroundColor Green
    } else {
        Write-Host "Failed to start service. Please check the logs." -ForegroundColor Red
    }
} catch {
    Write-Host "Failed to install service: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Press any key to continue..."
$host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") | Out-Null
"""

    try:
        ps1_path = Path.cwd() / "install_miniclaw_service.ps1"
        with open(ps1_path, "w") as f:
            f.write(ps1_content)

        print(f"Windows service installation script created: {ps1_path}")
        print("To complete installation:")
        print("1. Right-click on the PowerShell script and select 'Run with PowerShell'")
        print("   OR")
        print("1. Open PowerShell as Administrator")
        print("2. Navigate to this directory: cd '{}'".format(Path.cwd()))
        print("3. Run: .\\install_miniclaw_service.ps1")
        return True
    except Exception as e:
        print("Error creating Windows service files: {}".format(e))
        return False


def main():
    """Main function to initialize service setup."""
    if query_user_for_service_installation():
        success = install_service()
        if success:
            print("\nService setup completed successfully!")
            print("Please follow the instructions above to complete the installation.")
        else:
            print("\nService setup failed. You can manually set up the service later.")
    else:
        print("Skipping service setup. You can set up the service later by running:")
        print("  python -m miniclaw.service_installer")


if __name__ == "__main__":
    main()
