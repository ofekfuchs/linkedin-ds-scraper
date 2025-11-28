"""CSV persistence utilities."""

from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Set

from . import config
from .linkedin_scraper import JobPosting

LOGGER = logging.getLogger(__name__)

COLUMNS = [
    "collected_at",
    "job_title",
    "company_name",
    "location",
    "required_degree",
    "required_years_experience",
    "job_link",
]


def ensure_file(path: Path | None = None) -> Path:
    csv_path = path or config.CSV_PATH
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if not csv_path.exists():
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(COLUMNS)
    return csv_path


def _load_existing_links(csv_path: Path) -> Set[str]:
    links: Set[str] = set()
    if not csv_path.exists():
        return links
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "job_link" not in reader.fieldnames:
            return links
        for row in reader:
            link = (row.get("job_link") or "").strip()
            if link:
                links.add(link)
    return links


def append_rows(jobs: Iterable[JobPosting], path: Path | None = None) -> int:
    csv_path = ensure_file(path)
    existing_links = _load_existing_links(csv_path)
    timestamp = datetime.now(timezone.utc).isoformat()
    rows: List[List[str]] = []
    total_scraped = 0

    for job in jobs:
        total_scraped += 1
        link = job.job_link.strip()
        if link:
            if link in existing_links:
                LOGGER.debug("Skipping duplicate job link %s", link)
                continue
            existing_links.add(link)
        rows.append([timestamp, *job.as_row()])

    if not rows:
        LOGGER.info("All %s scraped rows were duplicates; CSV unchanged.", total_scraped)
        return 0

    with csv_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)

    removed = deduplicate_csv(csv_path)
    if removed:
        LOGGER.info("Removed %s historical duplicates while persisting new rows.", removed)

    return len(rows)


def deduplicate_csv(path: Path | None = None) -> int:
    """Ensure the CSV only contains one entry per job link."""
    csv_path = ensure_file(path)
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    if not rows:
        return 0

    seen_links: Set[str] = set()
    deduped: List[List[str]] = []
    removed = 0
    for row in rows:
        link = (row.get("job_link") or "").strip()
        if link and link in seen_links:
            removed += 1
            continue
        if link:
            seen_links.add(link)
        deduped.append([row.get(column, "") for column in COLUMNS])

    if removed:
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(COLUMNS)
            writer.writerows(deduped)

    return removed


def reset_file(path: Path | None = None) -> None:
    """Remove the CSV file so a fresh header is created on next write."""
    csv_path = (path or config.CSV_PATH)
    if csv_path.exists():
        csv_path.unlink()
    ensure_file(csv_path)


