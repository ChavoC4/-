from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_ACTION_MAP = {
    "продажби": "Продажби",
    "презалагане": "Презалагане",
    "прекратяване": "Прекратяване",
    "нов договор": "Нов договор",
}

_MATERIAL_MAP = {
    "жълт метал": "Жълт метал",
    "жалт метал": "Жълт метал",
    "злато": "Злато",
    "сребро": "Сребро",
    "техника": "Техника",
}

_DECIMAL_PATTERN = re.compile(r"-?\d+(?:[.,]\d+)?")


def normalize_spaces(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def normalize_key(text: str) -> str:
    return normalize_spaces(text).lower()


def normalize_action(text: str) -> str:
    key = normalize_key(text)
    for candidate, normalized in _ACTION_MAP.items():
        if candidate in key:
            return normalized
    return text.strip() or "Непознато"


def normalize_material(text: str) -> str:
    key = normalize_key(text)
    for candidate, normalized in _MATERIAL_MAP.items():
        if candidate in key:
            return normalized
    if not text.strip():
        return "-"
    return text.strip()


def parse_decimal(value: str | float | int | None) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    stripped = value.strip()
    if not stripped:
        return 0.0
    match = _DECIMAL_PATTERN.search(stripped)
    if not match:
        return 0.0
    candidate = match.group(0).replace(",", ".")
    try:
        return float(Decimal(candidate))
    except InvalidOperation:
        return 0.0
