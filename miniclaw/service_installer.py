#!/usr/bin/env python3
"""
Cross-platform service installer for MiniClaw.
Automatically detects the operating system and installs the appropriate service.
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path


def detect_os():
    """Detect the operating system."""
    return platform.system().lower()


def install_linux_service():
    """Install systemd service on Linux."""
    print("Installing MiniClaw systemd service on Linux...")
    
    # Check if systemd is available
    if not shutil.which("systemctl"):
        print("Error: systemd is not available on this system.")
        return False
    
    # Create service file
    service_content = """[Unit]
Description=MiniClaw AI Agent
After=network.target

[Service]
Type=simple
User={}
Group={}
WorkingDirectory={}
Environment=PATH=/home/{}/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/home/{}/.local/bin/miniclaw gateway
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/{}/.miniclaw

[Install]
WantedBy=multi-user.target
""".format(os.getenv("USER", "miniclaw"),
           os.getenv("USER", "miniclaw"),
           os.getcwd(),
           os.getenv("USER", "miniclaw"),
           os.getenv("USER", "miniclaw"),
           os.getenv("USER", "miniclaw"))
    
    # Write service file
    service_path = "/etc/systemd/system/miniclaw.service"
    try:
        # This will likely fail without sudo, so we'll instruct the user
        with open("miniclaw.service", "w") as f:
            f.write(service_content)
        
        print(f"Service file created: miniclaw.service")
        print("To complete installation, run the following commands with sudo:")
        print("  sudo cp miniclaw.service /etc/systemd/system/")
        print("  sudo systemctl daemon-reload")
        print("  sudo systemctl enable miniclaw")
        print("  sudo systemctl start miniclaw")
        return True
    except Exception as e:
        print(f"Error creating service file: {e}")
        return False


def install_macos_service():
    """Install launch daemon on macOS."""
    print("Installing MiniClaw launch daemon on macOS...")
    
    # Create plist file
    plist_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.miniclaw.agent</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>{}</string>
        <string>gateway</string>
    </array>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>WorkingDirectory</key>
    <string>{}</string>
    
    <key>StandardOutPath</key>
    <string>{}/.miniclaw/logs/miniclaw.out.log</string>
    
    <key>StandardErrorPath</key>
    <string>{}/.miniclaw/logs/miniclaw.err.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
""".format(shutil.which("miniclaw") or "miniclaw",
           os.getcwd(),
           str(Path.home()),
           str(Path.home()))
    
    # Write plist file
    plist_path = str(Path.home() / "Library" / "LaunchAgents" / "com.miniclaw.agent.plist")
    
    try:
        # Create directories if they don't exist
        Path(plist_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(plist_path, "w") as f:
            f.write(plist_content)
        
        print(f"Launch agent plist created: {plist_path}")
        print("To complete installation, run the following commands:")
        print(f"  launchctl load {plist_path}")
        print("Or reboot your system for the service to start automatically.")
        return True
    except Exception as e:
        print(f"Error creating plist file: {e}")
        return False


def install_windows_service():
    """Install Windows service."""
    print("Creating Windows service installation files...")
    
    # Create batch file for service installation
    bat_content = """@echo off
REM MiniClaw Windows Service Installation Script

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo This script requires administrator privileges.
    echo Please run as Administrator.
    pause
    exit /b 1
)

REM Create the service
sc create MiniClaw binPath= "\\"%~dp0miniclaw.exe\\" gateway" DisplayName= "MiniClaw AI Agent" start= auto

if %errorLevel% equ 0 (
    echo Service installed successfully.
    echo Starting the service...
    sc start MiniClaw
    if %errorLevel% equ 0 (
        echo Service started successfully.
    ) else (
        echo Failed to start service. Please check the logs.
    )
) else (
    echo Failed to install service.
)

pause
"""
    
    # Create PowerShell script for service installation
    ps1_content = """# MiniClaw Windows Service Installation Script (PowerShell)

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "This script requires administrator privileges." -ForegroundColor Red
    Write-Host "Please run as Administrator." -ForegroundColor Yellow
    pause
    exit 1
}

try {
    # Get the current directory
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $exePath = Join-Path $scriptDir "miniclaw.exe"
    
    # If miniclaw.exe doesn't exist, try to find it in PATH
    if (-not (Test-Path $exePath)) {
        $exePath = "miniclaw"
    }
    
    # Create the service
    $serviceName = "MiniClaw"
    New-Service -Name $serviceName -BinaryPathName "`"$exePath`" gateway" -DisplayName "MiniClaw AI Agent" -StartupType Automatic
    
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

Write-Host "Press any key to continue..."
$host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
"""
    
    try:
        with open("install_service.bat", "w") as f:
            f.write(bat_content)
        
        with open("install_service.ps1", "w") as f:
            f.write(ps1_content)
        
        print("Windows service installation files created:")
        print("  install_service.bat - Batch script for command prompt")
        print("  install_service.ps1 - PowerShell script")
        print("To install the service, run either script as Administrator.")
        return True
    except Exception as e:
        print(f"Error creating Windows service files: {e}")
        return False


def main():
    """Main function to detect OS and install appropriate service."""
    print("MiniClaw Service Installer")
    print("=" * 30)
    
    os_type = detect_os()
    print(f"Detected operating system: {os_type}")
    
    if os_type == "linux":
        success = install_linux_service()
    elif os_type == "darwin":  # macOS
        success = install_macos_service()
    elif os_type == "windows":
        success = install_windows_service()
    else:
        print(f"Unsupported operating system: {os_type}")
        return 1
    
    if success:
        print("\nService installation files created successfully!")
        print("Follow the instructions above to complete the installation.")
        return 0
    else:
        print("\nFailed to create service installation files.")
        return 1


if __name__ == "__main__":
    sys.exit(main())