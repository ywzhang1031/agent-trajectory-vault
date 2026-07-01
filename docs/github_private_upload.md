# Private GitHub Upload

本仓库默认 private-first。不要把当前 working dataset 创建为 public repo。

上传前先验证：

```bash
PYTHONPATH=src python3 -m unittest discover tests
PYTHONPATH=src python3 scripts/validate_dataset.py
PYTHONPATH=src python3 scripts/build_training_views.py
git status --short
```

用 GitHub CLI 创建 private repo 并推送：

```bash
gh repo create agent-trajectory-vault --private --source=. --remote=origin --push
```

如果远端仓库已存在：

```bash
git remote add origin https://github.com/<OWNER>/agent-trajectory-vault.git
git push -u origin main
```

如果后续要公开数据，建议新建单独分支或单独 release artifact，只包含人工 review 后的 subset，并在 release notes 里明确数据来源、脱敏策略、license 和 known limitations。
