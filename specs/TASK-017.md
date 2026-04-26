# TASK-017 - Skill 索引元数据

## 目标
建立 SkillPack 索引，让系统能用少量信息发现很多 skill。

## 产品层
SkillPack

## 范围内
- 从 `SKILL.md` 提取 name、description、path
- 新增 `list_skills()` 返回索引
- 新增 `GET /skills`
- 控制索引只包含摘要，不加载全文 instructions

## 范围外
- 自动路由
- 语义搜索
- skill 启用/禁用
- 市场分发

## 完成标准
- 多个 SkillPack 可被列出
- 列表输出不会包含完整长 prompt
- 测试覆盖至少两个 skill

## 验证
- `python3 -m unittest agent_prototype.tests.test_agent -v`
