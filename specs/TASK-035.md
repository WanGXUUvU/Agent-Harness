# TASK-035 - Context compact 摘要

## 目标
实现最小上下文压缩能力，把长会话压缩成摘要，减少后续请求上下文压力。

## 产品层
Context Management

## 背景
Codex 类产品通常提供 compact 能力。我们先实现手动触发，不做自动判断。

## 范围内
- 新增 `/compact` command 或 API
- 从当前 messages 生成摘要
- 把旧消息替换成一条 summary system/context message
- 保留最近若干条用户和 assistant 消息
- trace 记录 compact 事件

## 范围外
- 自动 token 估算触发
- 多层摘要树
- 高级记忆系统

## 实现步骤
1. 定义 compact 策略：保留最近 N 条，前面转摘要。
2. 新增 summary 生成函数。
3. 第一版可以用规则摘要，后续再接 LLM 摘要。
4. 修改 session state 并保存。
5. 写测试确认消息数量减少且后续还能对话。

## 完成标准
- compact 后 session 仍可继续运行。
- 旧上下文不会完全丢失，而是以摘要保留。
- trace 能看到 compact 发生过。

## 验证
- 构造长消息列表运行 compact 测试。
- `python3 -m unittest agent_prototype.tests.test_agent -v`

## Review 检查点
- 摘要是否明确标记为 summary。
- 是否保留最近关键消息。
- 是否避免自动破坏上下文。

