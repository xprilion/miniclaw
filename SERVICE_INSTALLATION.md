# MiniClaw Service Installation Guide

This guide explains how to set up MiniClaw to run as a background service that automatically starts on system boot.

## Automated Installation

The easiest way to install the service is to use the provided Python script:

```bash
python install_service.py
```

This script will detect your operating system and create the appropriate service configuration files.

## Manual Installation by Platform

### Linux (systemd)

1. Create the service file:
   ```bash
   sudo cp service_configs/linux/miniclaw.service /etc/systemd/system/
   ```

2. Reload systemd and enable the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable miniclaw
   ```

3. Start the service:
   ```bash
   sudo systemctl start miniclaw
   ```

4. Check the service status:
   ```bash
   sudo systemctl status miniclaw
   ```

### macOS

1. Copy the plist file to the LaunchAgents directory:
   ```bash
   mkdir -p ~/Library/LaunchAgents
   cp service_configs/macos/com.miniclaw.agent.plist ~/Library/LaunchAgents/
   ```

2. Load the service:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.miniclaw.agent.plist
   ```

3. To start immediately:
   ```bash
   launchctl start com.miniclaw.agent
   ```

### Windows

1. Open Command Prompt or PowerShell as Administrator.

2. Run either of the provided scripts:
   ```cmd
   service_configs\windows\install_service.bat
   ```
   
   Or in PowerShell:
   ```powershell
   .\service_configs\windows\install_service.ps1
   ```

## Managing the Service

### Linux
```bash
# Start service
sudo systemctl start miniclaw

# Stop service
sudo systemctl stop miniclaw

# Restart service
sudo systemctl restart miniclaw

# Check status
sudo systemctl status miniclaw

# View logs
sudo journalctl -u miniclaw -f
```

### macOS
```bash
# Start service
launchctl start com.miniclaw.agent

# Stop service
launchctl stop com.miniclaw.agent

# Restart service
launchctl unload ~/Library/LaunchAgents/com.miniclaw.agent.plist
launchctl load ~/Library/LaunchAgents/com.miniclaw.agent.plist

# View logs
tail -f ~/.miniclaw/logs/miniclaw.out.log
tail -f ~/.miniclaw/logs/miniclaw.err.log
```

### Windows
```cmd
# Start service
sc start Miniclaw

# Stop service
sc stop Miniclaw

# Restart service
sc stop Miniclaw
sc start Miniclaw

# View status
sc query Miniclaw
```

## Troubleshooting

### Common Issues

1. **Permission denied errors**: Make sure you're running the commands with appropriate privileges (sudo on Linux/macOS, Administrator on Windows).

2. **Service fails to start**: Check the logs for error messages:
   - Linux: `sudo journalctl -u miniclaw`
   - macOS: `tail -f ~/.miniclaw/logs/miniclaw.err.log`
   - Windows: Check Event Viewer

3. **Path issues**: Ensure that the miniclaw executable is in the system PATH or adjust the service configuration to use the full path.

### Uninstalling the Service

#### Linux
```bash
sudo systemctl stop miniclaw
sudo systemctl disable miniclaw
sudo rm /etc/systemd/system/miniclaw.service
sudo systemctl daemon-reload
```

#### macOS
```bash
launchctl unload ~/Library/LaunchAgents/com.miniclaw.agent.plist
rm ~/Library/LaunchAgents/com.miniclaw.agent.plist
```

#### Windows
```cmd
sc stop Miniclaw
sc delete Miniclaw
```