from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .models import AggregatedRow, ScrapedAction


def write_reports(
    output_dir: Path,
    rows: list[AggregatedRow],
    actions: list[ScrapedAction],
    run_time: datetime,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = run_time.strftime("%Y%m%d_%H%M%S")

    csv_path = output_dir / f"tracking_summary_{timestamp}.csv"
    md_path = output_dir / f"tracking_summary_{timestamp}.md"
    json_path = output_dir / f"tracking_raw_{timestamp}.json"
    latest_md_path = output_dir / "latest_summary.md"
    latest_csv_path = output_dir / "latest_summary.csv"
    latest_json_path = output_dir / "latest_raw.json"

    _write_csv(csv_path, rows)
    _write_markdown(md_path, rows, run_time)
    _write_json(json_path, actions, rows, run_time)

    latest_csv_path.write_text(csv_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_md_path.write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_json_path.write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")

    return {
        "csv": csv_path,
        "markdown": md_path,
        "json": json_path,
        "latest_csv": latest_csv_path,
        "latest_markdown": latest_md_path,
        "latest_json": latest_json_path,
    }


def _write_csv(path: Path, rows: list[AggregatedRow]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Действие", "Подразделение", "Брой", "Сума", "Тегло в гр"])
        for row in rows:
            writer.writerow(
                [
                    row.action,
                    row.subdivision,
                    _fmt_number(row.count),
                    _fmt_number(row.amount),
                    _fmt_number(row.weight_grams),
                ]
            )


def _write_markdown(path: Path, rows: list[AggregatedRow], run_time: datetime) -> None:
    lines = [
        f"# SOFCOM отчет ({run_time.isoformat(timespec='seconds')})",
        "",
        "| Действие | Подразделение | Брой | Сума | Тегло в гр |",
        "|---|---|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row.action} | {row.subdivision} | {_fmt_number(row.count)} | {_fmt_number(row.amount)} | {_fmt_number(row.weight_grams)} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_json(
    path: Path,
    actions: list[ScrapedAction],
    rows: list[AggregatedRow],
    run_time: datetime,
) -> None:
    payload = {
        "generated_at": run_time.isoformat(timespec="seconds"),
        "summary": [asdict(row) for row in rows],
        "actions": [asdict(action) for action in actions],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _fmt_number(value: float) -> str:
    rounded = round(value, 3)
    text = f"{rounded:.3f}"
    text = text.rstrip("0").rstrip(".")
    return text or "0"
