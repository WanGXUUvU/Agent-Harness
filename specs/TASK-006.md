# TASK-006 - SkillPack 文件结构

## 目标
建立项目自己的 SkillPack 文件结构，让 skill 从 Python 内存对象变成可读、可维护、可扩展的文件化工作流。

## 产品层
SkillPack

## 范围内
- 处理现有空文件 `agent_prototype/skills.py` 与目标目录 `agent_prototype/skills/` 的命名冲突
- 新建 `agent_prototype/skills/`
- 新建至少一个默认 SkillPack：`agent_prototype/skills/default/SKILL.md`
- 定义 `SKILL.md` 的最小字段：`name`、`description`、`instructions`
- 保留现有 `/run`、`/reset`、session、events 行为不变

## 范围外
- 自动选择 skill
- SkillPack 数据库存储
- SkillPack 创建 UI
- MCP
- 工具权限约束

## 完成标准
- 仓库里存在清晰的 SkillPack 目录
- 默认 skill 可以被人直接阅读
- 现有测试仍然通过

## 验证
- `python3 -m unittest agent_prototype.tests.test_agent -v`
