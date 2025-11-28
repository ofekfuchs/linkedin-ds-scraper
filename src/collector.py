"""High level orchestration of the scraping workflow."""

from __future__ import annotations

import logging
from typing import List

from . import config, csv_store, linkedin_scraper

LOGGER = logging.getLogger(__name__)


def collect_and_persist(limit: int | None = None) -> int:
    """Collect jobs and write them to the CSV. Returns the number of rows."""
    limit = limit or config.MAX_JOBS
    LOGGER.info("Collecting up to %s jobs from LinkedIn", limit)
    jobs = linkedin_scraper.collect_jobs(limit=limit)
    if not jobs:
        LOGGER.warning("No jobs were collected during this run.")
        return 0

    rows_written = csv_store.append_rows(jobs)
    LOGGER.info("Persisted %s rows to %s", rows_written, config.CSV_PATH)
    return rows_written


