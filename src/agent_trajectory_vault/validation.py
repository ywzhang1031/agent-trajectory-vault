from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent_trajectory_vault.jsonl_io import read_jsonl
from agent_trajectory_vault.redaction import REDACTION_PATTERNS
from agent_trajectory_vault.schema import SchemaError, validate_required_fields


REQUIRED_DATA_FILES = [
    "raw_index.jsonl",
    "trajectories.jsonl",
    "sft.jsonl",
    "dpo.jsonl",
    "grpo_rollouts.jsonl",
]


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


def _sensitive_categories(value: Any) -> list[str]:
    if isinstance(value, str):
        categories: list[str] = []
        seen: set[str] = set()
        for category, pattern, replacement in REDACTION_PATTERNS:
            redacted, count = pattern.subn(replacement, value)
            if count and redacted != value and category not in seen:
                categories.append(category)
                seen.add(category)
        return categories
    if isinstance(value, list):
        categories = []
        seen = set()
        for item in value:
            for category in _sensitive_categories(item):
                if category not in seen:
                    categories.append(category)
                    seen.add(category)
        return categories
    if isinstance(value, dict):
        categories = []
        seen = set()
        for item in value.values():
            for category in _sensitive_categories(item):
                if category not in seen:
                    categories.append(category)
                    seen.add(category)
        return categories
    return []


def _check_no_obvious_secrets(row: dict[str, Any], report: ValidationReport, label: str) -> None:
    for category in _sensitive_categories(row):
        report.errors.append(f"{label}: contains unredacted {category}")


def _load_required(path: Path, display_path: str, report: ValidationReport) -> list[dict[str, Any]]:
    if not path.exists():
        report.errors.append(f"{display_path}: missing required data file")
        return []
    try:
        return read_jsonl(path)
    except ValueError as exc:
        message = str(exc)
        path_text = str(path)
        if message.startswith(path_text):
            message = f"{display_path}{message[len(path_text):]}"
        report.errors.append(message)
        return []


def _validate_reference(
    ref: Any,
    *,
    field: str,
    canonical_ids: set[str],
    report: ValidationReport,
    label: str,
    index: int | None = None,
) -> None:
    reference_label = field if index is None else f"{field}[{index}]"
    if not isinstance(ref, str):
        report.errors.append(f"{label}: {reference_label} must be a string")
        return
    if ref not in canonical_ids:
        report.errors.append(f"{label}: unknown {reference_label}: {ref}")


def _validate_derived_references(
    row: dict[str, Any],
    *,
    canonical_ids: set[str],
    report: ValidationReport,
    label: str,
) -> None:
    found_reference = False
    if "trajectory_id" in row:
        found_reference = True
        _validate_reference(
            row["trajectory_id"],
            field="trajectory_id",
            canonical_ids=canonical_ids,
            report=report,
            label=label,
        )
    if "trajectory_ids" in row:
        found_reference = True
        refs = row["trajectory_ids"]
        if not isinstance(refs, list):
            report.errors.append(f"{label}: trajectory_ids must be a list")
        else:
            for index, ref in enumerate(refs):
                _validate_reference(
                    ref,
                    field="trajectory_ids",
                    canonical_ids=canonical_ids,
                    report=report,
                    label=label,
                    index=index,
                )
    if not found_reference:
        report.errors.append(f"{label}: missing trajectory_id or trajectory_ids")


def validate_dataset(root: Path) -> ValidationReport:
    report = ValidationReport()
    data_dir = root / "data"

    loaded = {
        filename: _load_required(data_dir / filename, f"data/{filename}", report)
        for filename in REQUIRED_DATA_FILES
    }

    for index, row in enumerate(loaded["raw_index.jsonl"], start=1):
        _check_no_obvious_secrets(row, report, f"data/raw_index.jsonl:{index}")

    canonical_ids: set[str] = set()
    for index, row in enumerate(loaded["trajectories.jsonl"], start=1):
        label = f"data/trajectories.jsonl:{index}"
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
        for index, row in enumerate(loaded[filename], start=1):
            label = f"data/{filename}:{index}"
            _check_no_obvious_secrets(row, report, label)
            _validate_derived_references(row, canonical_ids=canonical_ids, report=report, label=label)

    return report
