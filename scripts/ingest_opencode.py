#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from agent_trajectory_vault.jsonl_io import write_jsonl
from agent_trajectory_vault.opencode_loader import load_opencode_file
from agent_trajectory_vault.schema import utc_now_iso


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest one OpenCode transcript file.")
    parser.add_argument("source")
    parser.add_argument("--out", default="data/trajectories.jsonl")
    args = parser.parse_args()
    rows = load_opencode_file(Path(args.source), ingested_at=utc_now_iso())
    write_jsonl(Path(args.out), rows)
    print(f"wrote={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
