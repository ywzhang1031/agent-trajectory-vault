from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceFile:
    app: str
    path: Path


def _discover_sources(app: str, roots: list[Path], patterns: list[str]) -> list[SourceFile]:
    paths: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for pattern in patterns:
            paths.update(path for path in root.rglob(pattern) if path.is_file())
    return [SourceFile(app, path) for path in sorted(paths)]


def discover_codex_sources(root: Path | None = None) -> list[SourceFile]:
    roots = [root] if root is not None else [Path.home() / ".codex" / "sessions"]
    return _discover_sources("codex", roots, ["rollout-*.jsonl"])


def discover_cursor_sources(root: Path | None = None) -> list[SourceFile]:
    roots = (
        [root]
        if root is not None
        else [
            Path.home() / ".cursor" / "projects",
            Path.home() / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage",
        ]
    )
    return _discover_sources("cursor", roots, ["**/agent-transcripts/**/*.jsonl"])


def discover_opencode_sources(root: Path | None = None) -> list[SourceFile]:
    roots = (
        [root]
        if root is not None
        else [
            Path.home() / ".opencode",
            Path.home() / ".local" / "share" / "opencode",
        ]
    )
    db_sources = _discover_sources("opencode", roots, ["opencode.db"])
    if db_sources:
        return db_sources
    return _discover_sources("opencode", roots, ["storage/session_diff/ses_*.json", "ses_*.json"])
