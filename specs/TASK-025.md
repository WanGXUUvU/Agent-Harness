# TASK-025 - Plugin 包格式

## 目标
设计 SkillPack 和工具未来如何打包成可分发 plugin。

## 产品层
SkillPack + Tool Registry

## 范围内
- 定义 plugin 目录结构
- 定义 plugin manifest 最小字段
- 明确 plugin 与 SkillPack 的关系
- 明确本地安装路径

## 范围外
- 远程 marketplace
- 签名验证
- 自动升级
- UI 安装流程

## 完成标准
- 一个 plugin 能包含一个或多个 SkillPack
- 格式能支持未来工具和 MCP 配置
- 后续实现卡范围清楚

## 验证
- 仅 Review
