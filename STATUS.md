# STATUS

## Current Snapshot
- Phase: 第 2 阶段
- Task: 搭建最小可运行的 `AGENT` 原型
- Next: 学第一个工具调用，把 Agent 从“会聊天”推进到“会做事”
- Blocking: None

## Roadmap
- 阶段 A: OpenAI Responses API 最小调用
- 阶段 B: 接入到 `agent_prototype`
- 阶段 C: 单工具调用与状态管理
- 阶段 D: FastAPI 服务化与接口测试
- 阶段 E: RAG 基础与检索增强
- 阶段 F: 简历项目打磨与面试准备

## Done
- `todo-api` 第 1 阶段已收口
- `PATCH` 语义和核心测试已完成
- 已确认 FastAPI 适合做 Agent 的 HTTP 外壳
- 已创建 `agent-prototype/`
- 最小 Agent 闭环已跑通：输入、状态、工具、输出
- `agent_prototype` 已切到包式导入，但必须从父目录运行
- `agent_prototype` 的包导入和测试入口已修稳
- 已完成第一个 `POST /run` 接口的搭建与测试思路
- 当前学习重点将从本地骨架转向外部模型调用与最小工具接入
- `llm_client.py` 已建，但还需要修正请求字段和鉴权格式
- 下一步是把模型调用从“独立函数”接进 Agent 主流程
- 当前先验证 `BASE_URL` / `API_KEY` / `MODEL` 是否真的可用
- 第三方中转 API 已验证可用，能返回模型回复
- 当前 `agent.py` 里存在消息覆盖、角色拼写和状态类型不一致问题
- 单元测试已通过，下一步是实际调用 HTTP 接口确认端到端链路
- `/run` 端到端联调已验证通过，多轮对话已跑通

## Risks
- 不要一开始就做多 Agent
- 不要先做复杂 RAG
- 先把单 Agent 的输入、输出、状态边界定义清楚
