from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from agent_trajectory_vault.loaders import first_user_task, read_jsonl_events
from agent_trajectory_vault.redaction import redact_record
from agent_trajectory_vault.schema import make_trajectory, validate_required_fields


def _parse_arguments(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {"raw": value}
        return parsed if isinstance(parsed, dict) else {"raw": value}
    return {}


def _content_to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(part for part in parts if part.strip())
    return ""


def _append_tool_call(
    *,
    tool_calls: list[dict[str, Any]],
    commands: list[dict[str, Any]],
    tool: str,
    arguments: dict[str, Any],
    call_id: str | None = None,
) -> None:
    record: dict[str, Any] = {"tool": tool, "arguments": arguments}
    if call_id:
        record["call_id"] = call_id
    tool_calls.append(record)
    command = arguments.get("cmd") or arguments.get("command")
    if isinstance(command, str) and (tool.endswith("exec_command") or tool in {"shell", "bash", "exec_command"}):
        commands.append({"cmd": command, "exit_code": None})


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
                session_id = str(payload.get("id") or payload.get("session_id") or session_id)
                created_at = str(payload.get("timestamp") or created_at)
        elif event_type == "response_item":
            payload = event.get("payload")
            if isinstance(payload, dict):
                payload_type = payload.get("type")
                if payload_type == "user_message" and isinstance(payload.get("message"), str):
                    messages.append({"role": "user", "content": payload["message"]})
                elif payload_type == "agent_message" and isinstance(payload.get("message"), str):
                    messages.append({"role": "assistant", "content": payload["message"]})
                elif payload_type == "message":
                    role = payload.get("role")
                    content = _content_to_text(payload.get("content"))
                    if isinstance(role, str) and content:
                        messages.append({"role": role, "content": content})
                elif payload_type in {"function_call", "custom_tool_call"}:
                    tool = str(payload.get("name") or "unknown")
                    arguments = _parse_arguments(payload.get("arguments", payload.get("input")))
                    call_id = payload.get("call_id")
                    _append_tool_call(
                        tool_calls=tool_calls,
                        commands=commands,
                        tool=tool,
                        arguments=arguments,
                        call_id=call_id if isinstance(call_id, str) else None,
                    )
                elif payload_type in {"function_call_output", "custom_tool_call_output"}:
                    call_id = str(payload.get("call_id") or "")
                    output = payload.get("output")
                    observations.append({"tool": call_id, "content": output if isinstance(output, str) else ""})
                elif payload_type == "exec_command_end":
                    command = payload.get("command")
                    if isinstance(command, str):
                        commands.append({"cmd": command, "exit_code": payload.get("exit_code")})
                    output = payload.get("aggregated_output") or payload.get("stdout") or payload.get("stderr")
                    observations.append({"tool": "exec_command", "content": output if isinstance(output, str) else ""})
            else:
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

    if not messages and not tool_calls and not observations:
        return []

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
