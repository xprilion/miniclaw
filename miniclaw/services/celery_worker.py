"""Celery worker for executing MiniClaw jobs."""
from __future__ import annotations

import os
import traceback
from typing import Any, Dict

from celery import Celery
from celery.utils.log import get_task_logger

from ..core.app_state import AppState
from ..core.util import utc_now

# Configure Celery
celery_app = Celery('miniclaw')
celery_app.conf.update(
    broker_url=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

logger = get_task_logger(__name__)

# Global app state instance
app_state = None


def initialize_app_state() -> AppState:
    """Initialize the app state for Celery workers."""
    global app_state
    if app_state is None:
        app_state = AppState()
    return app_state


@celery_app.task(bind=True)
def execute_miniclaw_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a MiniClaw job using the agent."""
    try:
        # Initialize app state if needed
        state = initialize_app_state()

        job_id = job_data.get("id", "")
        job_name = job_data.get("name", job_id)
        prompt = job_data.get("prompt", "")

        logger.info(f"Executing job id={job_id} name={job_name}")

        # Execute the job using the agent
        result = state.agent.chat_with_updates(
            user_message=prompt,
            source="job",
            meta={"job_id": job_id, "job_name": job_name},
        )

        response_text = str(result.get("response") or "")

        # Send to Telegram if configured
        target_chat = str(job_data.get("send_to_telegram_chat_id") or "").strip()
        if target_chat and state.telegram:
            try:
                state.telegram.send_test_message(
                    target_chat,
                    f"[Job:{job_name or job_id}] {response_text}",
                )
            except Exception as exc:
                logger.error(f"Failed to send job output to Telegram: {exc}")

        logger.info(f"Job completed id={job_id} duration={result.get('duration_seconds', 0)}s")

        return {
            "ok": True,
            "job_id": job_id,
            "result": result,
            "completed_at": utc_now(),
        }

    except Exception as exc:
        logger.error(f"Job execution failed id={job_data.get('id', '')}: {exc}")
        logger.error(traceback.format_exc())

        return {
            "ok": False,
            "job_id": job_data.get("id", ""),
            "error": f"{exc.__class__.__name__}: {exc}",
            "traceback": traceback.format_exc(limit=10),
            "completed_at": utc_now(),
        }
