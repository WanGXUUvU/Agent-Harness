# TASK-006 - SkillPack 文件结构

## 目标
建立项目自己的 SkillPack 文件结构，让 skill 从 Python 内存对象变成可读、可维护、可扩展的文件化工作流。

## 产品层
SkillPack

## 背景
Codex 的 skill 以目录为单位，核心文件是 `SKILL.md`，可以继续扩展 `scripts/`、`references/`、`assets/`。我们第一步只做最小结构。

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

## 实现步骤
1. 确认 `agent_prototype/skills.py` 是否为空；如果为空，删除它以释放目录名。
2. 创建 `agent_prototype/skills/default/`。
3. 创建 `SKILL.md`，写入 `name`、`description`、`instructions` 三段。
4. instructions 只描述当前 agent 的默认行为，不引入新工具能力。
5. 不修改 agent 主循环，确保这是一个纯结构任务。

## 完成标准
- 仓库里存在清晰的 SkillPack 目录。
- 默认 skill 可以被人直接阅读。
- 现有测试仍然通过。

## 验证
- `python3 -m unittest agent_prototype.tests.test_agent -v`

## Review 检查点
- 文件结构是否和未来 `scripts/`、`references/`、`assets/` 兼容。
- 是否没有提前改 runtime。
- `SKILL.md` 是否足够短，适合后续渐进加载。

