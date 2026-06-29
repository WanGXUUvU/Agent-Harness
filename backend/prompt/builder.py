"""按固定顺序组装运行时 prompt。"""

from typing import Any, Optional

from backend.prompt.sections import (
    get_agent_overlay_section,
    get_available_skills_section,
    get_selected_skill_section,
    get_user_profile_section,
    get_workspace_rules_section,
)

PROMPT_DYNAMIC_BOUNDARY = "<DYNAMIC_CONTEXT_BOUNDARY>"


def build_runtime_system_prompt(
    *,
    available_skills: list[Any],
    selected_skill_content: Optional[str] = None,
    local_rules_text: Optional[str] = None,
    user_profile_text: Optional[str] = None,
    agent_overlay_text: Optional[str] = None,
) -> str:
    """基于已收集物料构建运行时 system prompt。"""
    # 1. 稳定 section：相同输入保持相同顺序
    stable_sections = [
        # 技能目录
        get_available_skills_section(available_skills),
        # 工作区局部规则
        get_workspace_rules_section(local_rules_text),
        # 用户级偏好与默认约束
        get_user_profile_section(user_profile_text),
        # Agent 专属 overlay
        get_agent_overlay_section(agent_overlay_text),
    ]

    # 2. 动态 section：只在本轮存在时追加
    dynamic_sections = [
        # 当前显式选中的 skill 正文
        get_selected_skill_section(selected_skill_content),
    ]

    # 3. 插入动态边界并组装最终 prompt
    parts = [section for section in stable_sections if section]
    dynamic_parts = [section for section in dynamic_sections if section]
    if dynamic_parts:
        parts.append(PROMPT_DYNAMIC_BOUNDARY)
        parts.extend(dynamic_parts)
    return "\n\n".join(parts)
