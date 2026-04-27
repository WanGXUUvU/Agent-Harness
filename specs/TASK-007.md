# TASK-007 - SkillPack Loader

## 目标
实现从文件系统读取 SkillPack 的 loader，让代码可以读取 `SKILL.md` 并转成内部对象。

## 产品层
SkillPack

## 范围内
- 新增 `SkillPack` 数据结构
- 读取 `agent_prototype/skills/<skill_name>/SKILL.md`
- 解析 `name`、`description`、`instructions`
- 处理 skill 不存在、字段缺失、文件格式错误
- 提供 `load_skill_pack(skill_name)` 函数

## 范围外
- 自动发现所有 skill
- 数据库存储
- UI
- 自动选择 skill

## 实现步骤
1. 新建 `agent_prototype/skill_loader.py` 或同等模块。
2. 定义 `SkillPack` Pydantic/dataclass 对象。
3. 实现读取 `SKILL.md` 的函数。
4. 第一版可以用简单 Markdown section 解析，不引入复杂依赖。
5. 对缺失字段返回清晰异常。
6. 为 default skill 写单元测试。

## 完成标准
- `load_skill_pack("default")` 能返回结构化对象。
- 读取失败时错误明确。
- 不影响现有 agent 行为。

## 验证
- `python3 -m unittest agent_prototype.tests.test_agent -v`

## Review 检查点
- loader 是否只负责读取和解析，不负责运行。
- 错误类型是否方便 API 层处理。
- 是否避免把 Markdown 格式设计得过度复杂。

