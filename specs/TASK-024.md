# TASK-024 - MCP 边界设计

## 目标
设计 MCP 接入边界，先明确系统怎么接，不急着实现 server。

## 产品层
Tool Registry

## 范围内
- 定义本地工具和 MCP 工具的共同抽象
- 明确工具发现、调用、错误、超时边界
- 记录需要哪些配置
- 输出后续 MCP 实现任务

## 范围外
- 真正启动 MCP server
- OAuth
- 远程工具市场
- 前端配置页

## 完成标准
- MCP 不再是模糊目标
- Tool Registry 有清晰扩展方向
- 可以创建 MCP 实现卡

## 验证
- 仅 Review
