# TASK-010 - 统一 Tool Registry

## 目标
把本地工具整理成统一注册入口，为后续 MCP、插件工具、SkillPack 工具约束做准备。

## 产品层
Tool Registry

## 范围内
- 定义工具注册结构
- 把 `echo_tool` 放进 registry
- 提供 `get_tool_schemas(tool_names=None)`
- 提供 `execute_tool_call(name, arguments)`
- 保持现有工具调用行为不变

## 范围外
- MCP 工具
- 外部 HTTP 工具
- 工具权限系统
- 并行工具调用

## 完成标准
- `Agent` 不再直接 `if tool_name == "echo_tool"`
- 新增工具只需要注册，不需要改 agent 主循环
- 现有工具调用测试通过

## 验证
- `python3 -m unittest agent_prototype.tests.test_agent -v`
