"""Scheduled agent jobs with optional Telegram delivery."""
from __future__ import annotations

import threading
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import ConfigStore
from .events import EventLog
from .job_store import JobStore
from .agent import MiniClawAgent
from .telegram import TelegramService
from .util import LOGGER

class SchedulerService:
    def __init__(
        self,
        config_store: ConfigStore,
        job_store: JobStore,
        event_log: EventLog,
        agent: MiniClawAgent,
        telegram: TelegramService,
    ) -> None:
        self._config_store = config_store
        self._job_store = job_store
        self._event_log = event_log
        self._agent = agent
        self._telegram = telegram
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="miniclaw-scheduler")
        self._next_run_epoch: Dict[str, float] = {}
        self._last_run_iso: Dict[str, str] = {}
        self._inflight: set[str] = set()
        self._thread.start()
        self._event_log.add("scheduler.started", "Scheduler service started", {})
        LOGGER.info("Scheduler service started")

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=5)
        self._event_log.add("scheduler.stopped", "Scheduler service stopped", {})
        LOGGER.info("Scheduler service stopped")

    def _jobs_from_store(self) -> tuple[bool, List[Dict[str, Any]]]:
        scheduler_cfg = self._config_store.get().get("scheduler", {})
        enabled = bool(scheduler_cfg.get("enabled", True))
        jobs = self._job_store.list()
        return enabled, jobs

    def _job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._job_store.get(str(job_id or "").strip().lower())

    def status(self) -> Dict[str, Any]:
        enabled, jobs = self._jobs_from_store()
        now = time.time()
        with self._lock:
            for key in list(self._next_run_epoch.keys()):
                if key not in {job["id"] for job in jobs}:
                    self._next_run_epoch.pop(key, None)
                    self._last_run_iso.pop(key, None)
                    self._inflight.discard(key)

            items: List[Dict[str, Any]] = []
            for job in jobs:
                job_id = job["id"]
                next_epoch = self._next_run_epoch.get(job_id)
                next_run = (
                    datetime.fromtimestamp(next_epoch, tz=timezone.utc).isoformat() if next_epoch is not None else None
                )
                items.append(
                    {
                        **job,
                        "inflight": job_id in self._inflight,
                        "next_run_at": next_run,
                        "last_run_at": self._last_run_iso.get(job_id),
                        "next_run_in_seconds": int(max(0, (next_epoch or now) - now)) if next_epoch else None,
                    }
                )

        return {
            "running": self._thread.is_alive(),
            "enabled": enabled,
            "jobs": items,
        }

    def trigger_now(self, job_id: str) -> Dict[str, Any]:
        job = self._job_by_id(job_id)
        if job is None:
            raise ValueError(f"Scheduler job not found: {job_id}")
        if not job.get("enabled", True):
            raise ValueError(f"Scheduler job is disabled: {job_id}")
        with self._lock:
            if job["id"] in self._inflight:
                return {"started": False, "reason": "already_running", "job_id": job["id"]}
            self._inflight.add(job["id"])
            self._next_run_epoch[job["id"]] = time.time() + int(job["interval_seconds"])
        threading.Thread(target=self._execute_job, args=(job,), daemon=True, name=f"scheduler-job-{job['id']}").start()
        return {"started": True, "job_id": job["id"]}

    def _execute_job(self, job: Dict[str, Any]) -> None:
        job_id = job["id"]
        started = time.time()
        self._event_log.add(
            "scheduler.job.started",
            "Scheduler job started",
            {
                "job": job,
            },
        )
        LOGGER.info("Scheduler job started id=%s name=%s", job_id, job.get("name"))
        try:
            result = self._agent.chat_with_updates(
                user_message=str(job["prompt"]),
                source="scheduler",
                meta={"job_id": job_id, "job_name": job.get("name")},
                status_callback=lambda status: self._event_log.add(
                    "scheduler.job.progress",
                    "Scheduler job progress",
                    {"job_id": job_id, "status": status},
                ),
            )
            response_text = str(result.get("response") or "")
            target_chat = str(job.get("send_to_telegram_chat_id") or "").strip()
            if target_chat:
                try:
                    self._telegram.send_test_message(
                        target_chat,
                        f"[Scheduler:{job.get('name') or job_id}] {response_text}",
                    )
                except Exception as exc:
                    self._event_log.add(
                        "scheduler.job.telegram_error",
                        "Failed to send scheduler output to Telegram",
                        {
                            "job_id": job_id,
                            "chat_id": target_chat,
                            "error": f"{exc.__class__.__name__}: {exc}",
                        },
                    )
            self._event_log.add(
                "scheduler.job.completed",
                "Scheduler job completed",
                {
                    "job_id": job_id,
                    "duration_seconds": round(time.time() - started, 3),
                    "response_preview": response_text[:220],
                },
            )
            LOGGER.info("Scheduler job completed id=%s duration=%.2fs", job_id, time.time() - started)
        except Exception as exc:
            self._event_log.add(
                "scheduler.job.error",
                "Scheduler job failed",
                {
                    "job_id": job_id,
                    "error": f"{exc.__class__.__name__}: {exc}",
                    "traceback": traceback.format_exc(limit=10),
                },
            )
            LOGGER.exception("Scheduler job failed id=%s", job_id)
        finally:
            with self._lock:
                self._inflight.discard(job_id)
                self._last_run_iso[job_id] = utc_now()

    def _run(self) -> None:
        while not self._stop_event.wait(timeout=1):
            enabled, jobs = self._jobs_from_store()
            now = time.time()
            job_ids = {job["id"] for job in jobs}
            with self._lock:
                for key in list(self._next_run_epoch.keys()):
                    if key not in job_ids:
                        self._next_run_epoch.pop(key, None)
                        self._last_run_iso.pop(key, None)
                        self._inflight.discard(key)

            if not enabled:
                continue

            for job in jobs:
                if not job.get("enabled", True):
                    continue
                job_id = job["id"]
                interval = int(job["interval_seconds"])
                should_run = False
                with self._lock:
                    next_epoch = self._next_run_epoch.get(job_id)
                    if next_epoch is None:
                        self._next_run_epoch[job_id] = now + interval
                        continue
                    if job_id in self._inflight:
                        continue
                    if now >= next_epoch:
                        should_run = True
                        self._inflight.add(job_id)
                        self._next_run_epoch[job_id] = now + interval
                if should_run:
                    threading.Thread(
                        target=self._execute_job,
                        args=(job,),
                        daemon=True,
                        name=f"scheduler-job-{job_id}",
                    ).start()