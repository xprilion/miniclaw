"""MiniClaw: minimal local agent with skills, tools, MCP, and Telegram."""
from __future__ import annotations

import os
from http.server import ThreadingHTTPServer

from .app_state import AppState
from .security import create_security_managers
from .server import make_handler
from .setup_wizard import run_setup_wizard
from .util import LOGGER, setup_logging


def run() -> None:
    """Start the HTTP server and all services (Telegram, scheduler)."""
    setup_logging()
    state = AppState()
    config = state.config_store.get()

    host = os.getenv("MINICLAW_HOST", str(config["server"].get("host") or "127.0.0.1"))
    port = int(os.getenv("MINICLAW_PORT", str(config["server"].get("port") or 8787)))

    handler_cls = make_handler(state)
    server = ThreadingHTTPServer((host, port), handler_cls)

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

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Keyboard interrupt received; shutting down")
        print("\nShutting down MiniClaw...")
    finally:
        state.scheduler.stop()
        state.telegram.stop()
        server.server_close()
        LOGGER.info("MiniClaw server stopped")


__all__ = ["run", "AppState", "make_handler", "create_security_managers", "run_setup_wizard"]
