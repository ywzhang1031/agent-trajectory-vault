from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any


def render_report(
    *,
    trajectories: list[dict[str, Any]],
    sft: list[dict[str, Any]],
    dpo: list[dict[str, Any]],
    grpo: list[dict[str, Any]],
    validation_errors: list[str],
    validation_warnings: list[str],
) -> str:
    source_counts = Counter(row.get("source_app", "unknown") for row in trajectories)
    review_counts = Counter(row.get("privacy_review_status", "unknown") for row in trajectories)
    lines = [
        "# Agent Trajectory Vault Report",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Trajectories: {len(trajectories)}",
        f"- SFT records: {len(sft)}",
        f"- DPO records: {len(dpo)}",
        f"- GRPO groups: {len(grpo)}",
        f"- Validation errors: {len(validation_errors)}",
        f"- Validation warnings: {len(validation_warnings)}",
        "",
        "## Source Coverage",
        "",
    ]
    for source, count in sorted(source_counts.items()):
        lines.append(f"- {source}: {count}")
    lines.extend(["", "## Privacy Review Status", ""])
    for status, count in sorted(review_counts.items()):
        lines.append(f"- {status}: {count}")
    if validation_errors:
        lines.extend(["", "## Validation Errors", ""])
        lines.extend(f"- {item}" for item in validation_errors)
    if validation_warnings:
        lines.extend(["", "## Validation Warnings", ""])
        lines.extend(f"- {item}" for item in validation_warnings)
    lines.append("")
    return "\n".join(lines)
