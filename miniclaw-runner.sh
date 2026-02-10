#!/usr/bin/bash
echo "Starting MiniClaw service..." >> /tmp/miniclaw-debug.log
date >> /tmp/miniclaw-debug.log
echo "Working directory: $(pwd)" >> /tmp/miniclaw-debug.log
echo "User: $(whoami)" >> /tmp/miniclaw-debug.log
echo "PATH: $PATH" >> /tmp/miniclaw-debug.log

cd /home/xprilion/.openclaw/workspace/miniclaw
echo "Changed to workspace directory" >> /tmp/miniclaw-debug.log

export PATH="/home/xprilion/.openclaw/workspace/miniclaw/.venv/bin:$PATH"
echo "Updated PATH" >> /tmp/miniclaw-debug.log

echo "About to execute python" >> /tmp/miniclaw-debug.log
exec /home/xprilion/.openclaw/workspace/miniclaw/.venv/bin/python -m miniclaw.cli.cli gateway