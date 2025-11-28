"""Background scheduler that refreshes LinkedIn job data."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from threading import Lock

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from . import config, collector

LOGGER = logging.getLogger(__name__)


class ScrapeScheduler:
    def __init__(self, interval_hours: int | None = None) -> None:
        self.interval_hours = interval_hours or config.SCRAPE_INTERVAL_HOURS
        self.scheduler = BackgroundScheduler()
        self._lock = Lock()
        self._next_run: datetime | None = None
        self._interval = timedelta(hours=self.interval_hours)

    def start(self) -> None:
        LOGGER.info("Starting scrape scheduler (interval=%sh)", self.interval_hours)
        trigger = IntervalTrigger(hours=self.interval_hours)
        next_fire = datetime.now(timezone.utc) + self._interval
        with self._lock:
            self._next_run = next_fire
        
        hours = int(self.interval_hours)
        minutes = int((self.interval_hours - hours) * 60)
        if minutes > 0:
            next_msg = f"Next scheduled run in {hours}h {minutes}m"
        else:
            next_msg = f"Next scheduled run in {hours}h"
        
        LOGGER.info("%s (at %s)", next_msg, next_fire.strftime("%Y-%m-%d %H:%M:%S UTC"))
        
        self.scheduler.add_job(
            self._run_job,
            trigger=trigger,
            next_run_time=datetime.now() + self._interval,
        )
        self.scheduler.start()

    def stop(self) -> None:
        if self.scheduler.running:
            LOGGER.info("Stopping scheduler")
            self.scheduler.shutdown(wait=False)

    def _run_job(self) -> None:
        LOGGER.info("Scheduled scrape started")
        collector.collect_and_persist()
        with self._lock:
            self._next_run = datetime.now(timezone.utc) + self._interval
            next_fire = self._next_run
        
        hours = int(self.interval_hours)
        minutes = int((self.interval_hours - hours) * 60)
        if minutes > 0:
            next_msg = f"Next scheduled run in {hours}h {minutes}m"
        else:
            next_msg = f"Next scheduled run in {hours}h"
        
        LOGGER.info("Scheduled scrape finished. %s (at %s)", next_msg, next_fire.strftime("%Y-%m-%d %H:%M:%S UTC"))

    def next_run_at(self) -> datetime | None:
        with self._lock:
            return self._next_run


