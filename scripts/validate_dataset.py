#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from agent_trajectory_vault.validation import validate_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate agent trajectory dataset files.")
    parser.add_argument("--root", default=".", help="Repository root containing data/*.jsonl")
    args = parser.parse_args()
    report = validate_dataset(Path(args.root).resolve())
    for warning in report.warnings:
        print(f"WARNING: {warning}")
    for error in report.errors:
        print(f"ERROR: {error}")
    print(f"errors={report.error_count} warnings={report.warning_count}")
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
