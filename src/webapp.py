"""Flask web server that exposes the CSV file and countdown timer."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from flask import Flask, jsonify, render_template_string, send_file

from . import csv_store
from .scheduler import ScrapeScheduler

LOGGER = logging.getLogger(__name__)


TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>LinkedIn Data Scientist Jobs - Israel</title>
    <style>
        :root {
            color-scheme: light;
            --primary: #0a66c2;
            --border: #d9e3ee;
            --muted: #5f6b7b;
        }
        * { box-sizing: border-box; }
        body {
            font-family: "Segoe UI", Tahoma, sans-serif;
            margin: 0;
            background: #f4f6f8;
            color: #1f2329;
        }
        main {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        header {
            margin-bottom: 1.5rem;
        }
        header h1 {
            margin: 0 0 0.75rem;
            font-size: 2rem;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 0.75rem;
        }
        .stat-card {
            background: #fff;
            border-radius: 12px;
            padding: 0.9rem 1rem;
            border: 1px solid var(--border);
            box-shadow: 0 10px 25px rgba(15, 23, 42, 0.05);
        }
        .stat-card span {
            display: block;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--muted);
        }
        .stat-card strong {
            font-size: 1.25rem;
        }
        .panel {
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 15px 35px rgba(15, 23, 42, 0.08);
            padding: 1.5rem;
        }
        .toolbar {
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1rem;
        }
        input[type="search"] {
            padding: 0.5rem 0.75rem;
            border: 1px solid var(--border);
            border-radius: 8px;
            min-width: 260px;
            flex: 1;
        }
        button {
            border: none;
            border-radius: 8px;
            padding: 0.6rem 1rem;
            font-weight: 600;
            cursor: pointer;
        }
        .btn-primary {
            background: var(--primary);
            color: #fff;
        }
        .btn-secondary {
            background: #fff;
            color: var(--primary);
            border: 1px solid var(--primary);
        }
        table {
            border-collapse: collapse;
            width: 100%;
            background: #fff;
            border-radius: 10px;
            overflow: hidden;
        }
        th, td {
            border: 1px solid var(--border);
            padding: 0.65rem 0.75rem;
            text-align: left;
            font-size: 0.95rem;
        }
        th {
            background: var(--primary);
            color: #fff;
            font-weight: 600;
        }
        tr:nth-child(even) td {
            background: #f9fbfd;
        }
        tr:hover td {
            background: #eef6ff;
        }
        footer {
            margin-top: 1.5rem;
            font-size: 0.9rem;
            color: var(--muted);
            text-align: center;
        }
        @media (max-width: 768px) {
            main { padding: 1rem; }
            input[type="search"] { min-width: 100%; }
            th, td { font-size: 0.85rem; }
        }
    </style>
  </head>
  <body>
    <main>
      <header>
        <h1>Open Data Scientist Roles in Israel</h1>
        <div class="stats-grid">
          <div class="stat-card">
            <span>Total rows</span>
            <strong>{{ row_count }}</strong>
          </div>
          <div class="stat-card">
            <span>Last updated</span>
            <strong>{{ last_updated_display or "N/A" }}</strong>
          </div>
          <div class="stat-card">
            <span>Next collection</span>
            <strong><span id="countdown"></span></strong>
          </div>
          <div class="stat-card">
            <span>Interval</span>
            <strong>{{ interval_hours }} h</strong>
          </div>
        </div>
      </header>
      <section class="panel">
        <div class="toolbar">
          <input type="search" id="searchInput" placeholder="Filter by title, company, or location">
          <div class="actions">
            <button class="btn-secondary" onclick="window.location.reload()">Refresh</button>
            <button class="btn-primary" onclick="window.location.href='/download'">Download CSV</button>
          </div>
        </div>
        <p class="meta" style="color: var(--muted); margin-bottom: 0.5rem;">
          Showing <span id="visibleCounter">{{ row_count }}</span> rows after filters.
        </p>
        <table>
          <thead>
            <tr>
              <th>Collected</th>
              <th>Job Title</th>
              <th>Company</th>
              <th>Location</th>
              <th>Degree</th>
              <th>Experience</th>
              <th>Link</th>
            </tr>
          </thead>
          <tbody>
            {% for row in rows %}
              <tr data-search="{{ row.search_blob }}">
                <td>{{ row.collected_at_display }}</td>
                <td>{{ row.job_title }}</td>
                <td>{{ row.company_name }}</td>
                <td>{{ row.location }}</td>
                <td>{{ row.required_degree }}</td>
                <td>{{ row.required_years_experience }}</td>
                <td><a href="{{ row.job_link }}" target="_blank" rel="noopener noreferrer">View</a></td>
              </tr>
            {% else %}
              <tr><td colspan="7">No data collected yet. Trigger a manual run.</td></tr>
            {% endfor %}
          </tbody>
        </table>
      </section>
      <footer>
        Data source: LinkedIn public job search · Only new links are appended each cycle
      </footer>
    </main>
    <script>
      let remaining = {{ countdown }};
      function formatTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        const pad = (v) => String(v).padStart(2, "0");
        return `${pad(hours)}h ${pad(minutes)}m ${pad(secs)}s`;
      }

      function updateCountdown() {
        const target = document.getElementById('countdown');
        if (!target) return;
        if (remaining <= 0) {
          target.innerText = "00h 00m 00s";
          return;
        }
        target.innerText = formatTime(remaining);
        remaining -= 1;
      }
      updateCountdown();
      setInterval(updateCountdown, 1000);

      const rows = Array.from(document.querySelectorAll('tbody tr[data-search]'));
      const searchInput = document.getElementById('searchInput');
      const visibleCounter = document.getElementById('visibleCounter');

      function applyFilters() {
        const term = (searchInput.value || "").toLowerCase();
        let visible = 0;

        rows.forEach((row) => {
          const matchesSearch = row.dataset.search.includes(term);
          row.style.display = matchesSearch ? "" : "none";
          if (matchesSearch) visible += 1;
        });

        visibleCounter.innerText = visible;
      }

      searchInput.addEventListener("input", applyFilters);
      applyFilters();
    </script>
  </body>
</html>
"""


def _load_rows(csv_path: Path) -> List[Dict[str, Any]]:
    if not csv_path.exists():
        return []
    try:
        df = pd.read_csv(csv_path)
    except pd.errors.EmptyDataError:
        return []
    return df.to_dict(orient="records")


def _seconds_until(next_run: datetime | None) -> int:
    if not next_run:
        return 0
    now = datetime.now(timezone.utc)
    delta = int((next_run - now).total_seconds())
    return max(delta, 0)


def _format_timestamp(raw: str | None) -> str:
    if not raw:
        return "N/A"
    cleaned = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(cleaned)
    except ValueError:
        return raw
    local_dt = dt.astimezone()
    return local_dt.strftime("%d %b %Y · %H:%M")


def _prepare_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    prepared: List[Dict[str, Any]] = []
    for row in rows:
        enriched = {
            **row,
            "collected_at_display": _format_timestamp(row.get("collected_at")),
            "search_blob": " ".join(
                [
                    str(row.get("job_title", "")).lower(),
                    str(row.get("company_name", "")).lower(),
                    str(row.get("location", "")).lower(),
                ]
            ),
        }
        prepared.append(enriched)
    return prepared


def create_app(scheduler: ScrapeScheduler) -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index():
        path = csv_store.ensure_file()
        rows = _load_rows(path)
        prepared_rows = _prepare_rows(rows[::-1])
        last_updated = rows[-1]["collected_at"] if rows else None
        countdown = _seconds_until(scheduler.next_run_at())
        interval_hours = int(round(scheduler.interval_hours))
        return render_template_string(
            TEMPLATE,
            rows=prepared_rows,
            row_count=len(rows),
            last_updated_display=_format_timestamp(last_updated),
            countdown=countdown,
            interval_hours=interval_hours,
        )

    @app.route("/download")
    def download():
        path = csv_store.ensure_file()
        LOGGER.info("Download requested for %s", path)
        return send_file(
            path,
            mimetype="text/csv",
            as_attachment=True,
            download_name=path.name,
        )

    @app.route("/api/jobs")
    def api_jobs():
        path = csv_store.ensure_file()
        rows = _load_rows(path)
        prepared_rows = _prepare_rows(rows[::-1])
        return jsonify({"count": len(rows), "jobs": prepared_rows})

    return app


