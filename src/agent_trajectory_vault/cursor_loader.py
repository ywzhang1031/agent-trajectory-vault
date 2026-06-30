from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_trajectory_vault.loaders import first_user_task, read_json_file, read_jsonl_events
from agent_trajectory_vault.redaction import redact_record
from agent_trajectory_vault.schema import make_trajectory, validate_required_fields


def _message_from_event(event: dict[str, Any]) -> dict[str, Any] | None:
    role = event.get("role")
    content = event.get("content")
    if isinstance(role, str) and isinstance(content, str):
        return {"role": role, "content": content}
    return None


def _tool_call_from_event(event: dict[str, Any]) -> dict[str, Any] | None:
    tool = event.get("tool")
    if not isinstance(tool, str):
        return None
    arguments = event.get("arguments")
    if not isinstance(arguments, dict):
        arguments = {}
    return {"tool": tool, "arguments": arguments}


def _load_cursor_payload(path: Path) -> dict[str, Any]:
    if path.suffix == ".jsonl":
        events = read_jsonl_events(path)
        return {
            "id": next((event.get("id") for event in events if event.get("id")), path.stem),
            "created_at": next((event.get("created_at") for event in events if event.get("created_at")), None),
            "messages": [message for event in events if (message := _message_from_event(event)) is not None],
            "tool_calls": [tool_call for event in events if (tool_call := _tool_call_from_event(event)) is not None],
        }
    payload = read_json_file(path)
    return payload if isinstance(payload, dict) else {}


def load_cursor_file(path: Path, *, ingested_at: str) -> list[dict[str, Any]]:
    payload = _load_cursor_payload(path)
    messages = [
        {"role": message["role"], "content": message["content"]}
        for message in payload.get("messages", [])
        if isinstance(message, dict) and isinstance(message.get("role"), str) and isinstance(message.get("content"), str)
    ]
    tool_calls = [
        tool_call
        for tool_call in payload.get("tool_calls", [])
        if isinstance(tool_call, dict) and isinstance(tool_call.get("tool"), str)
    ]
    commands = [
        {"cmd": tool_call["arguments"]["cmd"], "exit_code": None}
        for tool_call in tool_calls
        if tool_call.get("tool") == "shell"
        and isinstance(tool_call.get("arguments"), dict)
        and isinstance(tool_call["arguments"].get("cmd"), str)
    ]

    row = make_trajectory(
        source_app="cursor",
        source_session_id=str(payload.get("id") or path.stem),
        source_ref={"path": str(path)},
        created_at=str(payload.get("created_at") or ingested_at),
        ingested_at=ingested_at,
        task=first_user_task(messages),
        messages=messages,
        tool_calls=tool_calls,
        observations=[],
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
