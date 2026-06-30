from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent_trajectory_vault.jsonl_io import read_jsonl
from agent_trajectory_vault.schema import SchemaError, validate_required_fields


SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("api key", re.compile(r"\bsk-[A-Za-z0-9_-]{10,}\b")),
    ("github token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("github token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    (
        "private key",
        re.compile(
            r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
    ),
]
LOCAL_PATH_PATTERN = re.compile(r"/Users/evan(?:/[^\s\"'<>]*)?")


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)


def _as_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _check_no_obvious_secrets(row: dict[str, Any], report: ValidationReport, label: str) -> None:
    text = _as_text(row)
    for name, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            report.errors.append(f"{label}: contains unredacted {name}")
    if LOCAL_PATH_PATTERN.search(text):
        report.errors.append(f"{label}: contains unredacted local path")


def _load_optional(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return read_jsonl(path)


def _validate_reference(
    ref: Any,
    *,
    canonical_ids: set[str],
    report: ValidationReport,
    label: str,
) -> None:
    if not isinstance(ref, str):
        report.errors.append(f"{label}: trajectory_id must be a string")
        return
    if ref not in canonical_ids:
        report.errors.append(f"{label}: unknown trajectory_id: {ref}")


def _validate_derived_references(
    row: dict[str, Any],
    *,
    canonical_ids: set[str],
    report: ValidationReport,
    label: str,
) -> None:
    if "trajectory_id" in row:
        _validate_reference(row["trajectory_id"], canonical_ids=canonical_ids, report=report, label=label)
    elif "trajectory_ids" in row:
        refs = row["trajectory_ids"]
        if not isinstance(refs, list):
            report.errors.append(f"{label}: trajectory_ids must be a list")
            return
        for ref in refs:
            _validate_reference(ref, canonical_ids=canonical_ids, report=report, label=label)
    else:
        report.errors.append(f"{label}: missing trajectory_id or trajectory_ids")


def validate_dataset(root: Path) -> ValidationReport:
    report = ValidationReport()
    data_dir = root / "data"

    for index, row in enumerate(_load_optional(data_dir / "raw_index.jsonl"), start=1):
        _check_no_obvious_secrets(row, report, f"data/raw_index.jsonl[{index}]")

    canonical_ids: set[str] = set()
    for index, row in enumerate(_load_optional(data_dir / "trajectories.jsonl"), start=1):
        label = f"data/trajectories.jsonl[{index}]"
        try:
            validate_required_fields(row)
        except SchemaError as exc:
            report.errors.append(f"{label}: {exc}")

        trajectory_id = row.get("trajectory_id")
        if isinstance(trajectory_id, str):
            if trajectory_id in canonical_ids:
                report.errors.append(f"{label}: duplicate trajectory_id: {trajectory_id}")
            else:
                canonical_ids.add(trajectory_id)
        else:
            report.errors.append(f"{label}: trajectory_id must be a string")

        _check_no_obvious_secrets(row, report, label)

    for filename in ["sft.jsonl", "dpo.jsonl", "grpo_rollouts.jsonl"]:
        for index, row in enumerate(_load_optional(data_dir / filename), start=1):
            label = f"data/{filename}[{index}]"
            _check_no_obvious_secrets(row, report, label)
            _validate_derived_references(row, canonical_ids=canonical_ids, report=report, label=label)

    return report
