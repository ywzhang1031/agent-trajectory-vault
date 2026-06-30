from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_trajectory_vault.loaders import first_user_task, read_json_file, read_jsonl_events
from agent_trajectory_vault.redaction import redact_record
from agent_trajectory_vault.schema import make_trajectory, validate_required_fields


def _load_opencode_events(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".jsonl":
        return read_jsonl_events(path)
    payload = read_json_file(path)
    if isinstance(payload, dict) and isinstance(payload.get("events"), list):
        return [event for event in payload["events"] if isinstance(event, dict)]
    return []


def load_opencode_file(path: Path, *, ingested_at: str) -> list[dict[str, Any]]:
    events = _load_opencode_events(path)
    session_id = next((str(event.get("id")) for event in events if event.get("id")), path.stem)
    created_at = next((str(event.get("created_at")) for event in events if event.get("created_at")), ingested_at)
    messages: list[dict[str, Any]] = []
    tool_calls: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    commands: list[dict[str, Any]] = []

    for event in events:
        role = event.get("role")
        content = event.get("content")
        if isinstance(role, str) and isinstance(content, str):
            messages.append({"role": role, "content": content})

        tool = event.get("tool")
        if isinstance(tool, str):
            arguments = event.get("arguments")
            if not isinstance(arguments, dict):
                arguments = {}
            tool_calls.append({"tool": tool, "arguments": arguments})
            if isinstance(event.get("observation"), str):
                observations.append({"tool": tool, "content": event["observation"]})
            if tool == "shell" and isinstance(arguments.get("cmd"), str):
                commands.append({"cmd": arguments["cmd"], "exit_code": None})

    row = make_trajectory(
        source_app="opencode",
        source_session_id=session_id,
        source_ref={"path": str(path)},
        created_at=created_at,
        ingested_at=ingested_at,
        task=first_user_task(messages),
        messages=messages,
        tool_calls=tool_calls,
        observations=observations,
        commands=commands,
        edits=[],
        outcome="unknown",
        failure_type=None,
        privacy_review_status="auto_redacted",
        redaction_summary={},
        quality_flags=[],
    )
    redacted, summary = redact_record(row)
    redacted["redaction_summary"] = summary
    validate_required_fields(redacted)
    return [redacted]
