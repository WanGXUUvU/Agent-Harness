# TASK-011 - SkillPack 允许工具列表

## 目标
让 SkillPack 能声明允许使用哪些工具，Agent 只向模型暴露这些工具。

## 产品层
SkillPack + Tool Registry

## 范围内
- 在 `SKILL.md` 中定义 allowed tools 字段或段落
- loader 解析 allowed tools
- `Agent` 根据 loaded skill 获取工具 schema
- 未允许的工具调用返回明确错误

## 范围外
- 用户权限
- 运行时审批
- MCP
- 工具市场

## 完成标准
- 不同 SkillPack 能看到不同工具集合
- 工具调用仍然可追踪
- 测试覆盖允许和不允许两条路径

## 验证
- `python3 -m unittest agent_prototype.tests.test_agent -v`
