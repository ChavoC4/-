from __future__ import annotations

import re
from typing import Iterable

from .models import ScrapedAction
from .normalize import normalize_spaces, parse_decimal

_LABEL_SPLIT = re.compile(r"\s*[:\-]\s*")

ACTION_PATTERNS = (
    r"действие",
    r"тип действие",
    r"операция",
)
MATERIAL_PATTERNS = (
    r"група",
    r"подгрупа",
    r"материал",
    r"категория",
)
COUNT_PATTERNS = (r"брой",)
AMOUNT_PATTERNS = (r"сума",)
WEIGHT_PATTERNS = (
    r"тегло",
    r"гр",
)


def parse_actions_from_records(records: Iterable[dict[str, str]], source: str) -> list[ScrapedAction]:
    parsed: list[ScrapedAction] = []
    for record in records:
        action_text = _pick_value(record, ACTION_PATTERNS)
        material_text = _pick_value(record, MATERIAL_PATTERNS)
        count_text = _pick_value(record, COUNT_PATTERNS)
        amount_text = _pick_value(record, AMOUNT_PATTERNS)
        weight_text = _pick_value(record, WEIGHT_PATTERNS)

        fallback_text = normalize_spaces(" ".join(v for v in record.values() if v))
        if not action_text:
            action_text = _extract_by_hint(fallback_text, ACTION_PATTERNS)
        if not material_text:
            material_text = _extract_by_hint(fallback_text, MATERIAL_PATTERNS)
        if not count_text:
            count_text = _extract_by_hint(fallback_text, COUNT_PATTERNS)
        if not amount_text:
            amount_text = _extract_by_hint(fallback_text, AMOUNT_PATTERNS)
        if not weight_text:
            weight_text = _extract_by_hint(fallback_text, WEIGHT_PATTERNS)

        parsed.append(
            ScrapedAction(
                action_text=action_text or "Непознато",
                material_text=material_text or "-",
                count=parse_decimal(count_text),
                amount=parse_decimal(amount_text),
                weight_grams=parse_decimal(weight_text),
                raw_text=fallback_text,
                source=source,
                metadata=record,
            )
        )
    return parsed


def _pick_value(record: dict[str, str], patterns: tuple[str, ...]) -> str:
    for key, value in record.items():
        normalized = normalize_spaces(key).lower()
        if any(re.search(pattern, normalized) for pattern in patterns):
            return value
    return ""


def _extract_by_hint(text: str, patterns: tuple[str, ...]) -> str:
    lower = text.lower()
    for pattern in patterns:
        match = re.search(rf"{pattern}\s*[:\-]\s*([^,;|]+)", lower)
        if match:
            token = match.group(1)
            original_start = match.start(1)
            original_end = original_start + len(token)
            return normalize_spaces(text[original_start:original_end])
    if patterns == COUNT_PATTERNS or patterns == AMOUNT_PATTERNS or patterns == WEIGHT_PATTERNS:
        tokens = re.findall(r"-?\d+(?:[.,]\d+)?", text)
        if tokens:
            return tokens[0]
    chunks = _LABEL_SPLIT.split(text, maxsplit=1)
    if len(chunks) == 2:
        return normalize_spaces(chunks[1])
    return ""
