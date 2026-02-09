@echo off
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
sc create MiniClaw binPath= "\"%~dp0miniclaw.exe\" gateway" DisplayName= "MiniClaw AI Agent" start= auto

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