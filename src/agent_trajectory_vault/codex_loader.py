from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_trajectory_vault.loaders import first_user_task, read_jsonl_events
from agent_trajectory_vault.redaction import redact_record
from agent_trajectory_vault.schema import make_trajectory, validate_required_fields


def load_codex_file(path: Path, *, ingested_at: str) -> list[dict[str, Any]]:
    events = read_jsonl_events(path)
    session_id = path.stem
    created_at = ingested_at
    messages: list[dict[str, Any]] = []
    tool_calls: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    commands: list[dict[str, Any]] = []

    for event in events:
        event_type = event.get("type")
        if event_type == "session_meta":
            payload = event.get("payload", {})
            if isinstance(payload, dict):
                session_id = str(payload.get("id") or session_id)
                created_at = str(payload.get("timestamp") or created_at)
        elif event_type == "response_item":
            role = event.get("role")
            content = event.get("content")
            if isinstance(role, str) and isinstance(content, str):
                messages.append({"role": role, "content": content})
        elif event_type == "tool_call":
            tool = str(event.get("tool") or "unknown")
            arguments = event.get("arguments")
            if not isinstance(arguments, dict):
                arguments = {}
            tool_calls.append({"tool": tool, "arguments": arguments})
            if tool == "shell" and isinstance(arguments.get("cmd"), str):
                commands.append({"cmd": arguments["cmd"], "exit_code": None})
        elif event_type == "tool_result":
            tool = str(event.get("tool") or "unknown")
            content = event.get("content")
            observations.append({"tool": tool, "content": content if isinstance(content, str) else ""})

    row = make_trajectory(
        source_app="codex",
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
