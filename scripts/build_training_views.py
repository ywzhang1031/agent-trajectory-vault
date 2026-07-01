#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from agent_trajectory_vault.jsonl_io import read_jsonl, write_jsonl
from agent_trajectory_vault.training_views import build_dpo_records, build_grpo_rollouts, build_sft_records


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SFT, DPO, and GRPO views from canonical trajectories.")
    parser.add_argument("--root", default=".", help="Repository root containing data/trajectories.jsonl")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    trajectories = read_jsonl(root / "data" / "trajectories.jsonl")
    sft = build_sft_records(trajectories)
    dpo = build_dpo_records(trajectories)
    grpo = build_grpo_rollouts(trajectories)

    write_jsonl(root / "data" / "sft.jsonl", sft)
    write_jsonl(root / "data" / "dpo.jsonl", dpo)
    write_jsonl(root / "data" / "grpo_rollouts.jsonl", grpo)
    print(f"sft={len(sft)} dpo={len(dpo)} grpo_groups={len(grpo)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
