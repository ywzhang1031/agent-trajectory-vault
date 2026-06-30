from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


VALID_SOURCE_APPS = {"codex", "cursor", "opencode"}
VALID_OUTCOMES = {"success", "failure", "partial", "unknown"}
VALID_REVIEW_STATUS = {"auto_redacted", "needs_manual_review", "manual_reviewed"}
VALID_FAILURE_TYPES = {
    "planning_error",
    "tool_misuse",
    "code_edit_error",
    "test_misread",
    "context_drift",
    "instruction_following_error",
    "unknown",
}

REQUIRED_TRAJECTORY_FIELDS = [
    "trajectory_id",
    "source_app",
    "source_session_id",
    "source_ref",
    "created_at",
    "ingested_at",
    "task",
    "messages",
    "tool_calls",
    "observations",
    "commands",
    "edits",
    "outcome",
    "failure_type",
    "privacy_review_status",
    "redaction_summary",
    "quality_flags",
]


class SchemaError(ValueError):
    """Raised when a dataset row violates the canonical schema."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(*parts: str, prefix: str = "traj") -> str:
    normalized = json.dumps([str(part) for part in parts], ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


def validate_required_fields(row: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_TRAJECTORY_FIELDS if field not in row]
    if missing:
        raise SchemaError(f"missing trajectory fields: {', '.join(missing)}")
    if row["source_app"] not in VALID_SOURCE_APPS:
        raise SchemaError(f"invalid source_app: {row['source_app']}")
    if row["outcome"] not in VALID_OUTCOMES:
        raise SchemaError(f"invalid outcome: {row['outcome']}")
    if row["privacy_review_status"] not in VALID_REVIEW_STATUS:
        raise SchemaError(f"invalid privacy_review_status: {row['privacy_review_status']}")
    if row["failure_type"] is not None and row["failure_type"] not in VALID_FAILURE_TYPES:
        raise SchemaError(f"invalid failure_type: {row['failure_type']}")
    for list_field in ["messages", "tool_calls", "observations", "commands", "edits", "quality_flags"]:
        if not isinstance(row[list_field], list):
            raise SchemaError(f"{list_field} must be a list")
    if not isinstance(row["source_ref"], dict):
        raise SchemaError("source_ref must be an object")
    if not isinstance(row["redaction_summary"], dict):
        raise SchemaError("redaction_summary must be an object")


def make_trajectory(
    *,
    source_app: str,
    source_session_id: str,
    source_ref: dict[str, Any],
    created_at: str,
    ingested_at: str,
    task: str,
    messages: list[dict[str, Any]],
    tool_calls: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    commands: list[dict[str, Any]],
    edits: list[dict[str, Any]],
    outcome: str,
    failure_type: str | None,
    privacy_review_status: str,
    redaction_summary: dict[str, int],
    quality_flags: list[str],
) -> dict[str, Any]:
    row = {
        "trajectory_id": stable_id(source_app, source_session_id, task),
        "source_app": source_app,
        "source_session_id": source_session_id,
        "source_ref": source_ref,
        "created_at": created_at,
        "ingested_at": ingested_at,
        "task": task,
        "messages": messages,
        "tool_calls": tool_calls,
        "observations": observations,
        "commands": commands,
        "edits": edits,
        "outcome": outcome,
        "failure_type": failure_type,
        "privacy_review_status": privacy_review_status,
        "redaction_summary": redaction_summary,
        "quality_flags": quality_flags,
    }
    validate_required_fields(row)
    return row
