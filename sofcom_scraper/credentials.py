from __future__ import annotations

from pathlib import Path


def save_credentials_to_env(env_path: Path, username: str, password: str) -> None:
    env_path = env_path.resolve()
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    lines = _upsert(lines, "SOFCOM_USERNAME", username)
    lines = _upsert(lines, "SOFCOM_PASSWORD", password)

    content = "\n".join(lines).rstrip() + "\n"
    env_path.write_text(content, encoding="utf-8")


def _upsert(lines: list[str], key: str, value: str) -> list[str]:
    escaped_value = _quote_env(value)
    new_line = f"{key}={escaped_value}"
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(f"{key}="):
            lines[idx] = new_line
            return lines
    lines.append(new_line)
    return lines


def _quote_env(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
