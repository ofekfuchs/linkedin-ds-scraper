"""Command line interface for the LinkedIn scraper system."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
from typing import Optional

from werkzeug.serving import make_server

from . import collector, config, csv_store
from .scheduler import ScrapeScheduler
from .webapp import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

LOGGER = logging.getLogger(__name__)


def run_collect_once(limit: Optional[int]) -> None:
    collector.collect_and_persist(limit=limit)


def run_server(port: int) -> None:
    scheduler = ScrapeScheduler()
    scheduler.start()
    collector.collect_and_persist()
    flask_app = create_app(scheduler)
    server = make_server(host="0.0.0.0", port=port, app=flask_app)
    LOGGER.info("Web server started on http://localhost:%s", port)

    def shutdown(signum, frame):  # noqa: ARG001
        LOGGER.info("Shutdown signal received")
        scheduler.stop()
        server.shutdown()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    server.serve_forever()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="LinkedIn Data Scientist job collector",
    )
    subparsers = parser.add_subparsers(dest="command")

    collect_cmd = subparsers.add_parser(
        "collect-once",
        help="run a single scraping cycle and exit",
    )
    collect_cmd.add_argument(
        "--limit",
        type=int,
        default=config.MAX_JOBS,
        help="maximum number of jobs to collect",
    )

    serve_cmd = subparsers.add_parser(
        "serve",
        help="start the scheduler and web server (default)",
    )
    serve_cmd.add_argument(
        "--port",
        type=int,
        default=8000,
        help="port for the Flask web server (default: 8000)",
    )

    reset_cmd = subparsers.add_parser(
        "reset-data",
        help="delete the CSV file and recreate a fresh header",
    )

    parser.set_defaults(command="serve")
    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "collect-once":
        run_collect_once(limit=args.limit)
    elif args.command == "serve":
        run_server(port=args.port)
    elif args.command == "reset-data":
        csv_store.reset_file()
        LOGGER.info("Data file reset at %s", config.CSV_PATH)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()


