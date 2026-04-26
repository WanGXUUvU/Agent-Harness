# BUILD_PLAN

## M1 - 稳定 Agent Runtime

状态：已完成

已完成：
- 工具调用闭环
- 会话隔离
- SQLite 持久化
- Alembic 迁移基线
- 结构化执行事件

## M2 - SkillPack 基础

状态：当前阶段

目标：
从硬编码 prompt 行为，迁移到文件化 SkillPack。

任务：
- `TASK-006` SkillPack 文件结构
- `TASK-007` SkillPack loader
- `TASK-008` 将 SkillPack 注入 Agent Runtime
- `TASK-009` 通过 API 输入选择 SkillPack

## M3 - Tool Registry 与工具约束

状态：计划中

目标：
让工具具备产品级基础能力：可发现、可注册、可被 SkillPack 约束，并且可追踪。

任务：
- `TASK-010` Tool Registry
- `TASK-011` SkillPack 允许工具列表
- `TASK-012` 工具错误事件
- `TASK-013` 工具结果规范化

## M4 - Session 产品层

状态：计划中

目标：
把 session 存储从隐藏持久化能力，推进为用户可感知的产品能力。

任务：
- `TASK-014` Session 元数据
- `TASK-015` Session 列表和读取接口
- `TASK-016` Trace 回放接口

## M5 - Skill 管理

状态：计划中

目标：
支持很多 skill 同时存在，但不一次性把所有内容塞进上下文。

任务：
- `TASK-017` Skill 索引元数据
- `TASK-018` 渐进式 Skill 加载
- `TASK-019` Skill 启用/禁用配置
- `TASK-020` Skill 草稿创建流程

## M6 - 产品表面

状态：计划中

目标：
通过干净的用户入口暴露 Agent Runtime。

任务：
- `TASK-021` API 输出整理
- `TASK-022` 最小 CLI 入口
- `TASK-023` 前端规划任务卡

## M7 - 未来平台能力

状态：计划中

目标：
为 MCP、插件打包、多 Agent 和 Responses API 迁移做准备。

任务：
- `TASK-024` MCP 边界设计
- `TASK-025` Plugin 包格式
- `TASK-026` 模型适配层接口
- `TASK-027` Responses API 迁移计划
