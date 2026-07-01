from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_trajectory_vault.loaders import first_user_task, read_json_file, read_jsonl_events
from agent_trajectory_vault.redaction import redact_record
from agent_trajectory_vault.schema import make_trajectory, validate_required_fields


def _ms_to_iso(value: Any, fallback: str) -> str:
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat()
    return fallback


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _load_opencode_events(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".jsonl":
        return read_jsonl_events(path)
    payload = read_json_file(path)
    if isinstance(payload, dict) and isinstance(payload.get("events"), list):
        return [event for event in payload["events"] if isinstance(event, dict)]
    return []


def _build_opencode_row(
    *,
    source_path: Path,
    session_id: str,
    created_at: str,
    ingested_at: str,
    title: str,
    directory: str | None,
    messages: list[dict[str, Any]],
    tool_calls: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    commands: list[dict[str, Any]],
    edits: list[dict[str, Any]],
) -> dict[str, Any]:
    row = make_trajectory(
        source_app="opencode",
        source_session_id=session_id,
        source_ref={"path": str(source_path), "session_id": session_id, "directory": directory or ""},
        created_at=created_at,
        ingested_at=ingested_at,
        task=first_user_task(messages) if messages else title,
        messages=messages,
        tool_calls=tool_calls,
        observations=observations,
        commands=commands,
        edits=edits,
        outcome="unknown",
        failure_type=None,
        privacy_review_status="auto_redacted",
        redaction_summary={},
        quality_flags=[],
    )
    redacted, summary = redact_record(row)
    redacted["redaction_summary"] = summary
    validate_required_fields(redacted)
    return redacted


def _text_from_parts(parts: list[dict[str, Any]]) -> str:
    texts = [
        part["text"]
        for part in parts
        if part.get("type") == "text" and isinstance(part.get("text"), str) and part["text"].strip()
    ]
    return "\n".join(texts)


def _add_tool_part(
    *,
    part: dict[str, Any],
    tool_calls: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    commands: list[dict[str, Any]],
    edits: list[dict[str, Any]],
) -> None:
    tool = str(part.get("tool") or "unknown")
    state = part.get("state") if isinstance(part.get("state"), dict) else {}
    arguments = state.get("input") if isinstance(state.get("input"), dict) else {}
    call_id = part.get("callID")
    record: dict[str, Any] = {"tool": tool, "arguments": arguments}
    if isinstance(call_id, str):
        record["call_id"] = call_id
    tool_calls.append(record)

    output = state.get("output") or state.get("error")
    if isinstance(output, str) and output.strip():
        observations.append({"tool": tool, "content": output})

    if tool == "bash" and isinstance(arguments.get("command"), str):
        metadata = state.get("metadata") if isinstance(state.get("metadata"), dict) else {}
        commands.append({"cmd": arguments["command"], "exit_code": metadata.get("exit")})

    if tool in {"write", "edit"}:
        file_path = arguments.get("filePath") or arguments.get("path")
        if isinstance(file_path, str):
            edits.append({"tool": tool, "path": file_path})


def load_opencode_db(path: Path, *, ingested_at: str) -> list[dict[str, Any]]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        sessions = conn.execute(
            "SELECT id, title, directory, time_created FROM session ORDER BY time_created, id"
        ).fetchall()
        rows: list[dict[str, Any]] = []
        for session in sessions:
            session_id = str(session["id"])
            message_rows = conn.execute(
                "SELECT id, data FROM message WHERE session_id = ? ORDER BY time_created, id",
                (session_id,),
            ).fetchall()
            part_rows = conn.execute(
                "SELECT message_id, data FROM part WHERE session_id = ? ORDER BY time_created, id",
                (session_id,),
            ).fetchall()
            parts_by_message: dict[str, list[dict[str, Any]]] = {}
            for part_row in part_rows:
                part = _json_object(part_row["data"])
                parts_by_message.setdefault(str(part_row["message_id"]), []).append(part)

            messages: list[dict[str, Any]] = []
            tool_calls: list[dict[str, Any]] = []
            observations: list[dict[str, Any]] = []
            commands: list[dict[str, Any]] = []
            edits: list[dict[str, Any]] = []

            for message_row in message_rows:
                message_data = _json_object(message_row["data"])
                role = message_data.get("role")
                parts = parts_by_message.get(str(message_row["id"]), [])
                text = _text_from_parts(parts)
                if isinstance(role, str) and text:
                    messages.append({"role": role, "content": text})
                for part in parts:
                    if part.get("type") == "tool":
                        _add_tool_part(
                            part=part,
                            tool_calls=tool_calls,
                            observations=observations,
                            commands=commands,
                            edits=edits,
                        )

            rows.append(
                _build_opencode_row(
                    source_path=path,
                    session_id=session_id,
                    created_at=_ms_to_iso(session["time_created"], ingested_at),
                    ingested_at=ingested_at,
                    title=str(session["title"] or "unknown task"),
                    directory=session["directory"] if isinstance(session["directory"], str) else None,
                    messages=messages,
                    tool_calls=tool_calls,
                    observations=observations,
                    commands=commands,
                    edits=edits,
                )
            )
        return rows
    finally:
        conn.close()


def load_opencode_file(path: Path, *, ingested_at: str) -> list[dict[str, Any]]:
    if path.suffix == ".db":
        return load_opencode_db(path, ingested_at=ingested_at)

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

    return [
        _build_opencode_row(
            source_path=path,
            session_id=session_id,
            created_at=created_at,
            ingested_at=ingested_at,
            title="unknown task",
            directory=None,
            messages=messages,
            tool_calls=tool_calls,
            observations=observations,
            commands=commands,
            edits=[],
        )
    ]
