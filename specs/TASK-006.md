# TASK-006

## Goal
把当前 agent 的硬编码提示词和工具入口整理成最小可扩展的 `Prompt/Skill` 体系，为后续接入更完整的工具调用和 MCP 做准备。

## In Scope
- 将 `SYSTEM_PROMPT` 从代码里抽离成可配置入口
- 定义最小 `skill` 结构，能描述任务目标、约束和可用工具
- 让 `Agent` 在运行前能选择或注入一个 skill
- 把现有本地工具注册整理成统一入口
- 保持现有 `/run`、`/reset`、会话持久化和 `events` 行为不变

## Out of Scope
- 完整的技能市场
- 多 skill 自动路由
- 前端 skill 选择 UI
- 真正的 MCP server 实现
- 多 Agent 编排
- RAG

## Done when
- agent 不再依赖单一硬编码 system prompt
- 至少能用一个 skill 配置驱动一次完整运行
- 本地工具有统一注册和调用入口
- 现有工具调用闭环和测试不受影响
