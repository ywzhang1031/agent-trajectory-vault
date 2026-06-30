# Agent Trajectory Vault

[English README](docs/README.en.md)

## 项目初衷

这个仓库的目的是辅助我持续实践 agentic RL：把自己在 Codex、Cursor、OpenCode 等工具中完成真实 agent 任务时产生的轨迹，整理成结构化、可验证、可复盘的数据集。

我希望这些轨迹不只是个人日志，而是能够成为研究和训练 agent 行为的材料：它们记录了任务、上下文、工具调用、观察结果、错误、修正和最终结果，也保留了 agent 在真实工作流中暴露出的 planning、tool use、credit assignment、verification 等问题。

如果其中任何一部分数据、schema、清洗流程或训练视图能帮助模型学得更好，或者给其他研究者、工程师一点参考，那就是这个项目对开源世界的一点贡献。同时，这也是我在开源世界里留下自己足迹的一种方式：用真实实践沉淀可复用的材料，而不只是停留在想法和笔记里。

## 仓库定位

这是一个 private-first 的 agent trajectory 数据仓库。它从本机 Codex、Cursor、OpenCode 对话中导入轨迹，经过脱敏、标准化、校验后保存为 canonical dataset，并派生出 SFT、DPO、GRPO 训练视图。

第一版默认只推送到 private GitHub 仓库。公开发布必须单独人工 review。

## 数据文件

- `data/trajectories.jsonl`：脱敏后的 canonical trajectory。
- `data/sft.jsonl`：从高质量轨迹派生的 SFT 数据。
- `data/dpo.jsonl`：从人工审核对比中派生的 preference pairs。
- `data/grpo_rollouts.jsonl`：按任务组织的 rollout/reward 视图。
- `data/raw_index.jsonl`：本机来源索引，不包含 raw message 正文。

## 常用命令

```bash
PYTHONPATH=src python3 -m unittest discover tests
PYTHONPATH=src python3 scripts/weekly_update.py --dry-run
PYTHONPATH=src python3 scripts/validate_dataset.py
PYTHONPATH=src python3 scripts/build_training_views.py
```

## 隐私和安全边界

本仓库不提交原始未脱敏日志，不提交完整私有源码，不自动公开数据。自动脱敏只能降低风险，不能替代人工 review。任何公开发布都应重新检查 secrets、私有路径、个人信息、公司/客户上下文和第三方许可。

## 许可

代码、脚本和文档工具默认使用 MIT License。明确公开或分享的数据使用 `DATA_LICENSE.md` 中的 CC BY 4.0 和 Responsible Use 声明。私有工作数据不会因为仓库存在 license 文件而自动获得公开复用授权。
