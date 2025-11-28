## LinkedIn Data Scientist Job Collector

This project automates the collection of **Data Scientist** job postings in **Israel** from LinkedIn, stores the results in a CSV file, and exposes a small web interface for reviewing and downloading the data. A background scheduler refreshes the dataset every 12 hours by default (per assignment requirements), though you can shorten the interval temporarily for demos.

### Project structure

```
src/
  app.py           # CLI entry point (scraper + web server)
  collector.py     # High-level workflow coordination
  config.py        # Tunable constants (query, interval, paths)
  csv_store.py     # CSV persistence helpers
  linkedin_scraper.py # LinkedIn scraping + enrichment logic
  scheduler.py     # APScheduler wrapper for periodic runs
  webapp.py        # Flask server (table view + download + countdown)
data/
  linkedin_jobs.csv  # Auto-generated dataset (created on first run)
requirements.txt
README.md
```

### Prerequisites

- Windows 10 (tested), Python 3.11+
- A modern browser to view the dashboard
- Internet connectivity that allows requests to `www.linkedin.com`

> **Important:** Whenever the instructions mention `python`, use the Windows launcher command `py`.

### Setup

```powershell
cd C:\Users\ofekf\cursurProject\linkdinScraper
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

### Usage

#### 1. Start the scheduler + web server (preferred entry point)

```powershell
py -m src.app serve --port 8000
```

What happens:

- Performs an immediate scrape (so the dashboard isn't empty)
- Starts a background job that repeats every 12 hours (see `SCRAPE_INTERVAL_MINUTES`)
- Launches the Flask server on `http://localhost:8000`

The dashboard shows:

- A responsive table with friendly timestamps
- Text search across title/company/location (great for manual duplicate spot checks)
- Download button for the CSV
- A live countdown until the next scheduled scrape

Stop the service with `Ctrl+C`. The scheduler shuts down gracefully.

#### 2. Optional helper commands

- **One-off scrape (for manual snapshots)**
  ```powershell
  py -m src.app collect-once --limit 75
  ```
  Useful when you want to append a timestamp immediately without starting the server.

- **Reset the dataset**
  ```powershell
  py -m src.app reset-data
  ```
  Deletes `data\linkedin_jobs.csv` and recreates an empty file with just the header so you can demonstrate the full workflow from scratch. Run `collect-once` or `serve` afterward to repopulate it.

### Configuration

Modify `src/config.py` to adjust:

- `SEARCH_QUERY` or `LOCATION`
- `MAX_JOBS` per cycle
- `SCRAPE_INTERVAL_MINUTES` (and derived `SCRAPE_INTERVAL_HOURS`)
- User-Agent string, delays, storage paths

### Deliverables checklist

- ✅ Automated LinkedIn scraper with enrichment of degree & experience
- ✅ Persistent CSV showing multiple timestamps
- ✅ Web interface with filters, duplicate highlighting, download link, and countdown timer
- ✅ Clear setup and run instructions in a Git-tracked project

### Notes & tips

- LinkedIn occasionally changes HTML structure. Update the selectors in `src/linkedin_scraper.py` if parsing breaks.
- The unauthenticated endpoint is rate-limited. `MAX_JOBS` + `REQUEST_DELAY` keep the requests polite, but you can tweak as needed.
- The CSV writer automatically skips duplicate job links, so the dataset only keeps a single entry per LinkedIn posting.
- LinkedIn's public job detail pages sometimes return HTTP 429 (rate limited). When that happens the scraper still records the job but leaves degree/experience as "Not specified".
- On startup the server performs one immediate scrape, but the countdown reflects the next scheduled run (currently every 12 hours). If no new jobs appear between cycles, the log will note that all rows were duplicates and the CSV stays unchanged.
- For production use, consider rotating proxies and storing historical CSV snapshots separately.

Happy scraping!


