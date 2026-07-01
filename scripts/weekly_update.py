#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_trajectory_vault.codex_loader import load_codex_file
from agent_trajectory_vault.cursor_loader import load_cursor_file
from agent_trajectory_vault.jsonl_io import read_jsonl, upsert_jsonl, write_jsonl
from agent_trajectory_vault.opencode_loader import load_opencode_file
from agent_trajectory_vault.redaction import redact_text
from agent_trajectory_vault.reporting import render_report
from agent_trajectory_vault.schema import stable_id
from agent_trajectory_vault.source_discovery import discover_codex_sources, discover_cursor_sources, discover_opencode_sources
from agent_trajectory_vault.training_views import build_dpo_records, build_grpo_rollouts, build_sft_records
from agent_trajectory_vault.validation import validate_dataset


def _fixture_sources(fixture_root: Path) -> list[tuple[str, Path]]:
    return [
        ("codex", fixture_root / "codex" / "rollout.jsonl"),
        ("cursor", fixture_root / "cursor" / "session.json"),
        ("opencode", fixture_root / "opencode" / "session.jsonl"),
    ]


def _discovered_sources(apps: set[str]) -> list[tuple[str, Path]]:
    sources: list[tuple[str, Path]] = []
    if "codex" in apps:
        sources.extend((item.app, item.path) for item in discover_codex_sources())
    if "cursor" in apps:
        sources.extend((item.app, item.path) for item in discover_cursor_sources())
    if "opencode" in apps:
        sources.extend((item.app, item.path) for item in discover_opencode_sources())
    return sources


def _load_source(app: str, path: Path, ingested_at: str) -> list[dict[str, Any]]:
    if app == "codex":
        return load_codex_file(path, ingested_at=ingested_at)
    if app == "cursor":
        return load_cursor_file(path, ingested_at=ingested_at)
    if app == "opencode":
        return load_opencode_file(path, ingested_at=ingested_at)
    raise ValueError(f"unknown app: {app}")


def _raw_index_record(app: str, source_path: Path, records: int, ingested_at: str) -> dict[str, Any]:
    safe_source_path, _ = redact_text(str(source_path))
    return {
        "source_id": stable_id("source", app, str(source_path), prefix="source"),
        "source_app": app,
        "source_path": safe_source_path,
        "records": records,
        "ingested_at": ingested_at,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Import, validate, and report agent trajectories.")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--fixture-root", help="Use fixture transcripts instead of local app discovery")
    parser.add_argument("--apps", default="codex,cursor,opencode", help="Comma-separated source apps")
    parser.add_argument("--dry-run", action="store_true", help="Do not write data files")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    ingested_at = datetime.now(timezone.utc).isoformat()
    apps = {item.strip() for item in args.apps.split(",") if item.strip()}
    sources = _fixture_sources(Path(args.fixture_root).resolve()) if args.fixture_root else _discovered_sources(apps)

    imported: list[dict[str, Any]] = []
    raw_index: list[dict[str, Any]] = []
    for app, source_path in sources:
        if not source_path.exists():
            continue
        rows = _load_source(app, source_path, ingested_at)
        imported.extend(rows)
        raw_index.append(_raw_index_record(app, source_path, len(rows), ingested_at))

    existing = read_jsonl(root / "data" / "trajectories.jsonl")
    merged = existing
    if not args.dry_run:
        merged = upsert_jsonl(root / "data" / "trajectories.jsonl", imported, key="trajectory_id")
        upsert_jsonl(root / "data" / "raw_index.jsonl", raw_index, key="source_id")
        sft = build_sft_records(merged)
        dpo = build_dpo_records(merged)
        grpo = build_grpo_rollouts(merged)
        write_jsonl(root / "data" / "sft.jsonl", sft)
        write_jsonl(root / "data" / "dpo.jsonl", dpo)
        write_jsonl(root / "data" / "grpo_rollouts.jsonl", grpo)
        validation = validate_dataset(root)
        report = render_report(
            trajectories=merged,
            sft=sft,
            dpo=dpo,
            grpo=grpo,
            validation_errors=validation.errors,
            validation_warnings=validation.warnings,
        )
        (root / "reports").mkdir(parents=True, exist_ok=True)
        (root / "reports" / "latest.md").write_text(report, encoding="utf-8")

    print(f"dry_run={args.dry_run} imported={len(imported)} existing={len(existing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
