# TASK-020 - Skill 草稿创建流程

## 目标
实现最小“创建 skill 草稿”流程，让 agent 产品开始具备自扩展雏形。

## 产品层
SkillPack

## 范围内
- 新增创建 skill 草稿的服务函数
- 根据名称、描述、instructions 生成 `skills/<name>/SKILL.md`
- 做文件名安全校验
- 创建后默认 disabled 或 draft 状态

## 范围外
- 模型自动生成 skill
- 自动启用
- UI 编辑器
- marketplace

## 完成标准
- 系统能创建一个新的 SkillPack 草稿
- 草稿不会立刻影响运行时
- 可以通过 `GET /skills` 看见草稿

## 验证
- `python3 -m unittest agent_prototype.tests.test_agent -v`
