# DECISIONS

## 2026-04-27 - 使用 Agent Product Stack

决策：
使用五层产品框架：SkillPack、Tool Registry、Session Runtime、Execution Trace、Product Surface。

理由：
这样既能对齐 Codex、Claude Code 这类产品的方向，又能保留本项目自己的结构和命名体系。

## 2026-04-27 - 先做文件化 SkillPack

决策：
先把 skill 实现为 `skills/<name>/SKILL.md` 目录，再考虑数据库托管的 skill 创建、管理和市场化能力。

理由：
文件化 SkillPack 易读、易测、易手动修改，也更贴近现代 Agent 产品的 skill 机制。

## 2026-04-27 - 暂时保留当前模型适配层

决策：
在 SkillPack、Tool Registry、Session Runtime 和 Trace 层更清楚之前，暂时保留当前 Chat Completions 风格的模型适配层。

理由：
同时改模型 API 和 Agent 架构会混合风险。后续只要适配层边界清楚，就可以迁移到 Responses API，而不需要推倒整个运行时。

## 2026-04-27 - 任务卡必须保持小闭环

决策：
每张新任务卡只推进一个产品层，或一个清晰的集成边界。

理由：
小任务卡能让学习路径更清楚，也能让 Verify / Review 真正有意义。
