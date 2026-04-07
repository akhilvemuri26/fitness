from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.db.session import SessionLocal
from app.services.sync import HevySyncService, WhoopSyncService

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self) -> None:
        from app.core.config import get_settings

        settings = get_settings()
        self.scheduler = BackgroundScheduler(timezone=settings.canonical_timezone)
        self._started = False
        self._register_jobs()

    def _register_jobs(self) -> None:
        self.scheduler.add_job(
            self._reconcile_whoop,
            trigger="cron",
            minute="0,30",
            hour="8-23",
            id="reconcile-whoop",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self._sync_hevy,
            trigger="cron",
            minute="0,30",
            hour="8-23",
            id="sync-hevy",
            replace_existing=True,
        )

    def start(self) -> None:
        if not self._started:
            self.scheduler.start()
            self._started = True

    def shutdown(self) -> None:
        if self._started:
            self.scheduler.shutdown(wait=False)
            self._started = False

    def _reconcile_whoop(self) -> None:
        db = SessionLocal()
        try:
            WhoopSyncService(db).reconcile()
        except Exception:
            logger.exception("WHOOP reconciliation tick failed")
        finally:
            db.close()

    def _sync_hevy(self) -> None:
        db = SessionLocal()
        try:
            HevySyncService(db).sync()
        except Exception:
            logger.exception("Hevy sync tick failed")
        finally:
            db.close()


scheduler_service = SchedulerService()
