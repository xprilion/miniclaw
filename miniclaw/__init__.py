"""MiniClaw: minimal local agent with skills, tools, MCP, and Telegram."""
from __future__ import annotations

import os

from .core.app_state import AppState
from .security.security import create_security_managers
from .web.app import create_app
from .setup.setup_wizard import run_setup_wizard
from .core.util import LOGGER, setup_logging


def run() -> None:
    """Start the HTTP server and all services (Telegram, jobs)."""
    setup_logging()
    state = AppState()
    config = state.config_store.get()

    host = os.getenv("MINICLAW_HOST", str(config["server"].get("host") or "127.0.0.1"))
    port = int(os.getenv("MINICLAW_PORT", str(config["server"].get("port") or 8787)))

    app = create_app(state)

    state.event_log.add(
        "server.started",
        "MiniClaw server started",
        {
            "host": host,
            "port": port,
            "url": f"http://{host}:{port}",
        },
    )

    LOGGER.info("MiniClaw server starting host=%s port=%d", host, port)
    print(f"MiniClaw running at http://{host}:{port}")
    print(f"Config file: {state.config_store.path}")

    import uvicorn
    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    except KeyboardInterrupt:
        LOGGER.info("Keyboard interrupt received; shutting down")
        print("\nShutting down MiniClaw...")
    finally:
        state.job_service.stop()
        state.telegram.stop()
        LOGGER.info("MiniClaw server stopped")


__all__ = ["run", "AppState", "create_app", "create_security_managers", "run_setup_wizard"]