#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from agent_trajectory_vault.jsonl_io import read_jsonl, write_jsonl
from agent_trajectory_vault.redaction import redact_record


def main() -> int:
    parser = argparse.ArgumentParser(description="Redact a JSONL file.")
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    rows = []
    for row in read_jsonl(Path(args.input)):
        redacted, summary = redact_record(row)
        redacted["redaction_summary"] = summary
        rows.append(redacted)
    write_jsonl(Path(args.output), rows)
    print(f"wrote={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
