# MiniClaw Windows Service Installation Script (PowerShell)

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