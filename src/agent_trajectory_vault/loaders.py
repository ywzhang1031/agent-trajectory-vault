from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_jsonl_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSONL: {exc}") from exc
            if isinstance(value, dict):
                events.append(value)
    return events


def first_user_task(messages: list[dict[str, Any]]) -> str:
    for message in messages:
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
    return "unknown task"
