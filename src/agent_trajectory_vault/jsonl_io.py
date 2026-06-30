from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSONL: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected JSON object")
            rows.append(value)
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def upsert_jsonl(path: Path, records: Iterable[dict[str, Any]], *, key: str) -> list[dict[str, Any]]:
    existing = read_jsonl(path)
    order = []
    merged = {}
    for row in existing:
        if key not in row:
            raise ValueError(f"existing record missing key: {key}")
        row_key = row[key]
        if row_key in merged:
            raise ValueError(f"duplicate existing key: {row_key}")
        order.append(row_key)
        merged[row_key] = row
    for record in records:
        if key not in record:
            raise ValueError(f"record missing key: {key}")
        record_key = record[key]
        if record_key not in merged:
            order.append(record_key)
        merged[record_key] = record
    result = [merged[item_key] for item_key in order]
    write_jsonl(path, result)
    return result
