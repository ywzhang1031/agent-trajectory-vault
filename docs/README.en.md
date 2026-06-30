# Agent Trajectory Vault

## Motivation

This repository supports my hands-on exploration of agentic RL by turning my own Codex, Cursor, and OpenCode agent-task trajectories into a structured, validated, and reviewable dataset.

The goal is not to publish raw personal logs, but to preserve useful learning signals from real agent workflows: tasks, context, tool calls, observations, errors, fixes, outcomes, and failure modes. If any part of this data, schema, cleaning pipeline, or training view helps future models or gives other researchers and engineers a useful reference, then it has contributed something back to the open-source ecosystem.

## Scope

This is a private-first data repository. It imports local agent conversations, redacts sensitive material, normalizes them into canonical trajectories, validates the result, and derives SFT, DPO, and GRPO-oriented training views.

The first version targets a private GitHub repository. Public release requires a separate manual review.

## Commands

Currently available:

```bash
PYTHONPATH=src python3 -m unittest discover tests
```

Available after later tasks:

```bash
PYTHONPATH=src python3 scripts/weekly_update.py --dry-run
PYTHONPATH=src python3 scripts/validate_dataset.py
PYTHONPATH=src python3 scripts/build_training_views.py
```

## Privacy

Raw unredacted logs, full private source files, and unrevised sensitive content must not be committed. Automated redaction reduces risk but does not replace manual review before any public release.
