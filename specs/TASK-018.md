# TASK-018 - 渐进式 Skill 加载

## 目标
实现类似 Codex/Claude 的渐进加载：先看 skill 摘要，选中后再加载全文。

## 产品层
SkillPack

## 范围内
- 分离 `SkillSummary` 和 `LoadedSkill`
- 默认只读取 summary
- 运行时才读取完整 `SKILL.md`
- 补测试证明列表接口不加载全文

## 范围外
- token 预算算法
- embedding 选择
- 自动路由
- cache 失效通知

## 完成标准
- skill 列表轻量
- agent 运行时能拿到完整 skill
- loader 结构为后续自动选择做好准备

## 验证
- `python3 -m unittest agent_prototype.tests.test_agent -v`
