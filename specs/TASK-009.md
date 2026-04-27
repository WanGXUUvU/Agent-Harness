# TASK-009 - 显式选择 SkillPack

## 目标
允许 API 请求显式指定要使用的 SkillPack，例如 `skill_name="default"`。

## 产品层
API / SkillPack

## 范围内
- `AgentInput` 增加可选 `skill_name`
- service 层根据 `skill_name` 加载 skill
- 未传入时使用 default
- skill 不存在时返回清晰错误
- session 中记录本轮使用的 skill

## 范围外
- 自动选择 skill
- skill enable/disable
- 多 skill 组合
- UI skill 选择器

## 实现步骤
1. 修改 `AgentInput` schema，增加 `skill_name: str | None`。
2. 在 service 层确定 effective skill。
3. 加载失败时转成 API 可读错误。
4. 在 trace 或 response metadata 中记录 skill 名称。
5. 测试 default 路径和指定 skill 路径。

## 完成标准
- 请求不传 skill 时行为不变。
- 请求传入存在的 skill 时能使用对应 instructions。
- 请求传入不存在的 skill 时不会静默回退。

## 验证
- `python3 -m unittest agent_prototype.tests.test_agent -v`

## Review 检查点
- 错误是否清楚。
- session 是否记录了实际使用的 skill。
- API 是否保持向后兼容。

