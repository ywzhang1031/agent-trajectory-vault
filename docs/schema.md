# Schema

`data/trajectories.jsonl` 是 canonical source of truth。其他训练视图都从它派生，避免多份数据互相漂移。

每一行 trajectory 至少包含这些字段：

- `trajectory_id`
- `source_app`
- `source_session_id`
- `source_ref`
- `created_at`
- `ingested_at`
- `task`
- `messages`
- `tool_calls`
- `observations`
- `commands`
- `edits`
- `outcome`
- `failure_type`
- `privacy_review_status`
- `redaction_summary`
- `quality_flags`

派生文件：

- `data/sft.jsonl`：从成功且已通过隐私边界的 trajectory 派生，包含 `messages` 和 `target`。
- `data/dpo.jsonl`：从人工修正记录派生，包含 `chosen` / `rejected`。
- `data/grpo_rollouts.jsonl`：按 `task` 聚合 rollout，包含 `trajectory_ids`、`rollouts`、`reward` 和 verifier notes。

数据入口应优先写入 `data/trajectories.jsonl`，再运行：

```bash
PYTHONPATH=src python3 scripts/build_training_views.py
PYTHONPATH=src python3 scripts/validate_dataset.py
```
