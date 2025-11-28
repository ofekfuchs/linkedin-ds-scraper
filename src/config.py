from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

# Search parameters
SEARCH_QUERY = "Data Scientist"
LOCATION = "Israel"
RESULTS_PER_PAGE = 25
MAX_JOBS = 75  # stop after this many records per run

# Scraping behaviour
# Default interval set to 12 hours per assignment requirements.
SCRAPE_INTERVAL_MINUTES = 12 * 60
SCRAPE_INTERVAL_HOURS = SCRAPE_INTERVAL_MINUTES / 60
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 1.5
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

CSV_PATH = BASE_DIR / "data" / "linkedin_jobs.csv"



