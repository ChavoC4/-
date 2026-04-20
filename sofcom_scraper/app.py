from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from .aggregator import SALES_SUBDIVISIONS, TOP_LEVEL_ACTIONS, aggregate_actions
from .config import AppConfig
from .models import AggregatedRow
from .reporting import write_reports
from .scraper import SofcomScraper


def run_once(config: AppConfig) -> dict[str, object]:
    scraper = SofcomScraper(config)
    actions = scraper.scrape_tracking_actions()
    rows = aggregate_actions(actions)
    ordered_rows = _ordered_rows(rows)

    run_time = datetime.now(tz=ZoneInfo(config.timezone))
    report_files = write_reports(config.output_dir, ordered_rows, actions, run_time)

    return {
        "run_time": run_time,
        "total_raw_actions": len(actions),
        "rows": ordered_rows,
        "report_files": report_files,
    }


def _ordered_rows(rows: list[AggregatedRow]) -> list[AggregatedRow]:
    order_map: dict[tuple[str, str], int] = {}
    idx = 0
    for material in SALES_SUBDIVISIONS:
        order_map[("Продажби", material)] = idx
        idx += 1
    for action in TOP_LEVEL_ACTIONS:
        if action == "Продажби":
            continue
        order_map[(action, "-")] = idx
        idx += 1

    def sort_key(row: AggregatedRow) -> tuple[int, str, str]:
        return order_map.get((row.action, row.subdivision), 10_000), row.action, row.subdivision

    return sorted(rows, key=sort_key)
