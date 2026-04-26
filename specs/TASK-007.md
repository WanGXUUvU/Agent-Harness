# TASK-007 - SkillPack Loader

## 目标
实现一个最小 SkillPack loader，可以按名称从磁盘读取 `SKILL.md`。

## 产品层
SkillPack

## 范围内
- 新建 `agent_prototype/skill_loader.py`
- 定义 `LoadedSkill` 数据结构
- 实现 `load_skill(name)`
- 实现 `list_skill_names()`
- 为 loader 补最小测试

## 范围外
- 自动路由
- 数据库 skill
- 插件市场
- 前端展示

## 完成标准
- 能加载 `default` SkillPack
- 加载结果包含名称、描述、完整 instructions、路径
- 缺失 skill 时有明确错误

## 验证
- `python3 -m unittest agent_prototype.tests.test_agent -v`
