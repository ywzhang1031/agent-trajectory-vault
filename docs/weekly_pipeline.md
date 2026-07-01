# Weekly Pipeline

手动 dry run：

```bash
PYTHONPATH=src python3 scripts/weekly_update.py --dry-run
```

fixture 验证流程：

```bash
PYTHONPATH=src python3 scripts/weekly_update.py --fixture-root tests/fixtures
PYTHONPATH=src python3 scripts/validate_dataset.py
PYTHONPATH=src python3 scripts/build_training_views.py
```

常规本机导入流程：

```bash
PYTHONPATH=src python3 scripts/weekly_update.py
PYTHONPATH=src python3 scripts/validate_dataset.py
```

后续自动化应遵守这些边界：

- 只导入增量 session，避免每周全量重扫大目录。
- 导入后先运行 validation，再允许 push。
- 报告写入 `reports/latest.md`；未来可以扩展到 `reports/weekly/YYYY-MM-DD.md`。
- 只推送 private GitHub 仓库；公开 subset 必须单独人工 review。
