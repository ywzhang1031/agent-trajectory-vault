from __future__ import annotations

from collections import defaultdict
from typing import Any

from .schema import stable_id


def _last_assistant_message(messages: list[dict[str, Any]]) -> str | None:
    for message in reversed(messages):
        if message.get("role") == "assistant" and str(message.get("content", "")).strip():
            return str(message["content"]).strip()
    return None


def build_sft_records(trajectories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for trajectory in trajectories:
        if trajectory.get("outcome") != "success":
            continue
        if trajectory.get("privacy_review_status") == "needs_manual_review":
            continue
        target = _last_assistant_message(trajectory.get("messages", []))
        if not target:
            continue
        records.append(
            {
                "record_id": stable_id("sft", trajectory["trajectory_id"], prefix="sft"),
                "trajectory_id": trajectory["trajectory_id"],
                "task": trajectory["task"],
                "messages": trajectory["messages"],
                "target": target,
                "source_app": trajectory["source_app"],
                "quality_flags": trajectory.get("quality_flags", []),
            }
        )
    return records


def build_dpo_records(trajectories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for trajectory in trajectories:
        correction = trajectory.get("manual_correction")
        if not isinstance(correction, dict):
            continue
        chosen = correction.get("chosen")
        rejected = correction.get("rejected")
        reason = correction.get("reason", "manual correction")
        if not chosen or not rejected:
            continue
        records.append(
            {
                "record_id": stable_id("dpo", trajectory["trajectory_id"], prefix="dpo"),
                "trajectory_id": trajectory["trajectory_id"],
                "task": trajectory["task"],
                "chosen": chosen,
                "rejected": rejected,
                "failure_type": trajectory.get("failure_type") or "unknown",
                "reason": reason,
                "review_status": trajectory.get("privacy_review_status", "auto_redacted"),
            }
        )
    return records


def build_grpo_rollouts(trajectories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trajectory in trajectories:
        by_task[trajectory["task"]].append(trajectory)

    groups: list[dict[str, Any]] = []
    for task, task_trajectories in sorted(by_task.items()):
        trajectory_ids = [row["trajectory_id"] for row in task_trajectories]
        rollouts = [
            {
                "trajectory_id": row["trajectory_id"],
                "messages": row.get("messages", []),
                "tool_calls": row.get("tool_calls", []),
                "observations": row.get("observations", []),
                "outcome": row.get("outcome", "unknown"),
            }
            for row in task_trajectories
        ]
        reward = [1.0 if row.get("outcome") == "success" else 0.0 for row in task_trajectories]
        groups.append(
            {
                "group_id": stable_id("grpo", task, prefix="group"),
                "task_id": stable_id("task", task, prefix="task"),
                "trajectory_ids": trajectory_ids,
                "rollouts": rollouts,
                "reward": reward,
                "reward_source": "heuristic",
                "verifier_notes": "Reward is 1.0 for success and 0.0 otherwise until a stronger verifier is added.",
                "group_status": "ready" if len(task_trajectories) > 1 else "partial",
            }
        )
    return groups
