# Redaction Policy

本仓库的原则是 private-first：先保留本机完整上下文，进入仓库前只提交 redacted trajectory。自动脱敏的目标是降低误传风险，不等于公开发布许可。

自动脱敏覆盖的主要类别：

- API keys 和 bearer tokens
- GitHub tokens
- Cookie、Set-Cookie、session identifiers
- emails 和 phone numbers
- 本机绝对路径
- 保守识别到的 private/internal/company repo URL
- SSH private key block

风险标记：

- `auto_redacted`：脚本已完成基础脱敏，但尚未人工 review。
- `needs_manual_review`：记录仍有上下文、许可、隐私或质量风险；不得进入公开候选集。
- `manual_reviewed`：人工确认过的记录，可作为后续 public subset 候选，但公开前仍需要最终检查。

原始未脱敏日志保留在 Codex、Cursor、OpenCode 各自的本机目录中，不提交到本仓库。公开发布任何数据前，需要重新检查 secrets、个人信息、私有路径、客户/公司上下文和第三方许可。
