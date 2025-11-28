"""
Utilities for fetching public LinkedIn job postings via the unauthenticated
guest search endpoint.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional

import requests
from bs4 import BeautifulSoup

from . import config

LOGGER = logging.getLogger(__name__)

SEARCH_URL = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
)

DEGREE_PATTERNS = [
    ("Bachelor", re.compile(r"\b(b\.?\s*sc|b\.?\s*s\.?|b\.?\s*a\.?|bachelor'?s?)\b", re.IGNORECASE)),
    ("Master", re.compile(r"\b(m\.?\s*sc|m\.?\s*s\.?|master'?s?)\b", re.IGNORECASE)),
    ("PhD", re.compile(r"\b(ph\.?\s*d\.?|doctorate|doctoral)\b", re.IGNORECASE)),
]

DEGREE_REQUIRED_HINTS = (
    "require",
    "required",
    "must",
    "minimum",
    "at least",
    "need",
    "looking for",
)
DEGREE_PREFERRED_HINTS = (
    "prefer",
    "preferred",
    "advantage",
    "nice to have",
    "plus",
    "bonus",
)

YEARS_RANGE_PATTERN = re.compile(
    r"(?P<min>\d{1,2})\s*(?:-|to)\s*(?P<max>\d{1,2})\s*(?:years?|yrs?)",
    flags=re.IGNORECASE,
)
YEARS_PATTERN = re.compile(
    r"(?P<years>\d{1,2})(?P<plus>\s*\+)?\s*(?:years?|yrs?)\s+of\s+experience",
    flags=re.IGNORECASE,
)
YEARS_FALLBACK_PATTERN = re.compile(
    r"(?:at\s+least\s+|minimum\s+of\s+)?(?P<years>\d{1,2})(?P<plus>\s*\+)?\s*(?:years?|yrs?)",
    flags=re.IGNORECASE,
)


@dataclass
class JobPosting:
    title: str
    company: str
    location: str
    degree: str
    years_experience: str
    job_link: str

    def as_row(self) -> List[str]:
        return [
            self.title,
            self.company,
            self.location,
            self.degree,
            self.years_experience,
            self.job_link,
        ]


def _request_html(start: int) -> str:
    params = {
        "keywords": config.SEARCH_QUERY,
        "location": config.LOCATION,
        "start": start,
    }
    headers = {
        "User-Agent": config.USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
    }
    response = requests.get(
        SEARCH_URL, params=params, headers=headers, timeout=config.REQUEST_TIMEOUT
    )
    response.raise_for_status()
    return response.text


def _parse_cards(html: str) -> Iterable[JobPosting]:
    soup = BeautifulSoup(html, "html.parser")
    for card in soup.select("li"):
        base_card = card.select_one("div.base-search-card")
        if not base_card:
            continue

        title = (
            base_card.select_one("h3.base-search-card__title") or card.select_one("h3")
        )
        company = base_card.select_one("h4.base-search-card__subtitle")
        location = base_card.select_one("span.job-search-card__location")
        link_tag = base_card.select_one("a.base-card__full-link")

        if not (title and company and location and link_tag):
            continue

        job = JobPosting(
            title=title.get_text(strip=True),
            company=company.get_text(strip=True),
            location=location.get_text(strip=True),
            degree="Not specified",
            years_experience="Not specified",
            job_link=link_tag.get("href", "").split("?")[0],
        )
        yield job


def _extract_degree(text: str) -> Optional[str]:
    matches: List[tuple[str, str]] = []
    lower = text.lower()
    for label, pattern in DEGREE_PATTERNS:
        for found in pattern.finditer(text):
            start, end = found.start(), found.end()
            window = lower[max(0, start - 50) : min(len(text), end + 50)]
            category = "neutral"
            if any(hint in window for hint in DEGREE_PREFERRED_HINTS):
                category = "preferred"
            if any(hint in window for hint in DEGREE_REQUIRED_HINTS):
                category = "required"
            matches.append((label, category))

    if not matches:
        return None

    order = {"Bachelor": 0, "Master": 1, "PhD": 2}
    for category in ("required", "neutral", "preferred"):
        eligible = [label for label, cat in matches if cat == category]
        if eligible:
            return min(eligible, key=lambda lbl: order[lbl])
    return None


def _extract_years(text: str) -> Optional[str]:
    match = YEARS_RANGE_PATTERN.search(text)
    if match:
        return f"{match.group('min')} years"

    match = YEARS_PATTERN.search(text)
    if match:
        return f"{match.group('years')} years"

    match = YEARS_FALLBACK_PATTERN.search(text)
    if match:
        return f"{match.group('years')} years"
    return None


def _enrich_job(job: JobPosting) -> None:
    if not job.job_link:
        return

    headers = {
        "User-Agent": config.USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        resp = requests.get(job.job_link, headers=headers, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        LOGGER.warning("Failed to load job detail %s: %s", job.job_link, exc)
        return

    soup = BeautifulSoup(resp.text, "html.parser")
    description_container = soup.select_one("div.description__text")
    if not description_container:
        description_container = soup.select_one("div.show-more-less-html__markup")
    if not description_container:
        return

    description_text = description_container.get_text(separator=" ", strip=True)
    degree = _extract_degree(description_text)
    years = _extract_years(description_text)

    if degree:
        job.degree = degree
    if years:
        job.years_experience = years


def collect_jobs(limit: int = config.MAX_JOBS) -> List[JobPosting]:
    """Fetch and enrich job postings up to the requested limit."""
    collected: List[JobPosting] = []
    start = 0

    while len(collected) < limit:
        try:
            html = _request_html(start)
        except requests.RequestException as exc:
            LOGGER.error("LinkedIn request failed: %s", exc)
            break

        new_jobs = list(_parse_cards(html))
        if not new_jobs:
            break

        collected.extend(new_jobs)
        start += config.RESULTS_PER_PAGE

    collected = collected[:limit]

    for idx, job in enumerate(collected, start=1):
        _enrich_job(job)
        if idx % 3 == 0:
            time.sleep(config.REQUEST_DELAY)

    return collected


