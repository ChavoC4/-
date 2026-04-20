from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from threading import Timer
from time import sleep
import webbrowser
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

from sofcom_scraper.app import run_once
from sofcom_scraper.config import AppConfig
from sofcom_scraper.webapp import create_web_app


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
LOGGER = logging.getLogger("sofcom-scraper")


def main() -> int:
    parser = argparse.ArgumentParser(description="SOFCOM daily tracking scraper")
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Run scraper immediately once and exit.",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run scheduler daemon that triggers daily at configured time.",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Start local web UI on localhost.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Web UI host (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Web UI port (default: 8080).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not auto-open browser when web UI starts.",
    )
    args = parser.parse_args()

    load_dotenv()
    config = AppConfig.from_env()

    if args.run_now:
        return _run_once_and_print(config)
    if args.daemon:
        return _run_scheduler(config)
    if args.web:
        return _run_web_ui(config, args.host, args.port, auto_open=not args.no_browser)

    # Default mode for non-technical users: start local dashboard directly.
    return _run_web_ui(config, args.host, args.port, auto_open=not args.no_browser)


def _run_once_and_print(config: AppConfig) -> int:
    try:
        result = run_once(config)
    except Exception as exc:  # pragma: no cover - runtime path
        LOGGER.exception("Scrape run failed: %s", exc)
        return 2

    run_time = result["run_time"]
    total_actions = result["total_raw_actions"]
    files = result["report_files"]
    LOGGER.info(
        "Run completed at %s, raw actions: %s, latest markdown: %s",
        run_time,
        total_actions,
        files["latest_markdown"],
    )
    return 0


def _run_scheduler(config: AppConfig) -> int:
    timezone = ZoneInfo(config.timezone)
    scheduler = BackgroundScheduler(timezone=timezone)

    scheduler.add_job(
        lambda: _run_once_and_print(config),
        trigger="cron",
        hour=config.schedule_hour,
        minute=config.schedule_minute,
        id="sofcom-daily-scrape",
        replace_existing=True,
    )

    scheduler.start()
    next_run = scheduler.get_jobs()[0].next_run_time
    LOGGER.info(
        "Scheduler started. Daily run set for %02d:%02d (%s). Next run: %s",
        config.schedule_hour,
        config.schedule_minute,
        config.timezone,
        next_run.astimezone(timezone).isoformat() if next_run else "unknown",
    )
    LOGGER.info("Press Ctrl+C to stop.")

    try:
        while True:
            # Keep the process alive for daily schedule execution.
            sleep(30)
    except (KeyboardInterrupt, SystemExit):  # pragma: no cover - runtime path
        scheduler.shutdown(wait=False)
        LOGGER.info("Scheduler stopped at %s", datetime.now(tz=timezone).isoformat())
    return 0


def _run_web_ui(config: AppConfig, host: str, port: int, auto_open: bool) -> int:
    app = create_web_app(config)
    url = f"http://{host}:{port}"
    browser_url = f"http://127.0.0.1:{port}" if host in {"0.0.0.0", "::"} else url
    LOGGER.info("Starting local web UI at %s", url)
    if auto_open:
        Timer(1.0, lambda: webbrowser.open(browser_url)).start()
    app.run(host=host, port=port, debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
