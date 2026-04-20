from __future__ import annotations

from collections import OrderedDict

from .models import AggregatedRow, ScrapedAction
from .normalize import normalize_action, normalize_material

TOP_LEVEL_ACTIONS = ("Продажби", "Презалагане", "Прекратяване", "Нов договор")
SALES_SUBDIVISIONS = ("Жълт метал", "Злато", "Сребро", "Техника")


def _row_key(action: str, subdivision: str) -> tuple[str, str]:
    return normalize_action(action), normalize_material(subdivision)


def aggregate_actions(actions: list[ScrapedAction]) -> list[AggregatedRow]:
    grouped: OrderedDict[tuple[str, str], AggregatedRow] = OrderedDict()
    for item in actions:
        action = normalize_action(item.action_text)
        subdivision = normalize_material(item.material_text)

        if action != "Продажби":
            subdivision = "-"

        key = _row_key(action, subdivision)
        if key not in grouped:
            grouped[key] = AggregatedRow(action=action, subdivision=subdivision)
        row = grouped[key]
        row.count += item.count
        row.amount += item.amount
        row.weight_grams += item.weight_grams

    _ensure_required_rows(grouped)
    return list(grouped.values())


def _ensure_required_rows(grouped: OrderedDict[tuple[str, str], AggregatedRow]) -> None:
    for material in SALES_SUBDIVISIONS:
        key = ("Продажби", material)
        grouped.setdefault(key, AggregatedRow(action="Продажби", subdivision=material))

    for action in TOP_LEVEL_ACTIONS:
        if action == "Продажби":
            continue
        key = (action, "-")
        grouped.setdefault(key, AggregatedRow(action=action, subdivision="-"))

