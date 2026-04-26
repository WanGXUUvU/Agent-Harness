# SPEC

## 产品目标
把当前原型打造成一个真正可用的本地优先 Agent 产品，方向对齐 Codex、Claude Code 和 Copilot：它能运行会话、加载可复用 SkillPack、调用工具、保留可追踪执行过程，并给用户干净的最终输出。

## 产品框架：Agent Product Stack
本项目使用自己的产品框架：**Agent Product Stack**。

这个框架分为五层：

1. SkillPack：以文件形式保存的可复用工作流说明。
2. Tool Registry：统一暴露本地工具和未来 MCP 工具。
3. Session Runtime：隔离、持久化、可重置、可回放的 Agent 会话运行层。
4. Execution Trace：解释 Agent 做了什么的结构化事件轨迹。
5. Product Surface：先提供 API，再扩展 CLI 或 UI，并保持用户输出干净。

## 当前状态
当前原型已经具备：

- FastAPI 应用，已有 `/run` 和 `/reset`
- SQLite 会话持久化
- Alembic 迁移基线
- 基础本地工具 `echo_tool`
- 结构化 `AgentEvent` 输出
- 覆盖 Agent 直接调用和 API 调用的测试

## 目标用户
- 正在学习真实 Agent 产品如何搭建的构建者。
- 未来需要可复用 Agent skill 和工具工作流的开发者。
- 未来希望使用清晰 Agent 界面，而不是阅读原始日志的终端用户。

## 技术约束
- 现阶段保留当前 Chat Completions 风格的模型适配层。
- 每一步都要保持现有 `/run`、`/reset`、session 存储和 events 行为稳定。
- 优先实现文件化 SkillPack，再考虑数据库托管的 skill 管理。
- 每张任务卡都要足够小，可以通过测试或手动 API 调用验证。
- 在核心运行时清晰之前，暂不进入 MCP、前端 UI 和多 Agent 路由。

## 本轮规划暂不包含
- 生产级安全加固
- 计费、账号、鉴权和云部署
- 完整插件市场
- 完整 MCP 实现
- 复杂前端产品 UI

## 完成标准
- SkillPack 可以被发现、加载、选择，并影响 Agent 行为。
- 工具可以被注册，并能被选中的 SkillPack 约束。
- Session 和 trace 保持稳定、可检查。
- 项目从本地原型走向产品级 Agent Runtime 的路线清晰。
