"""system prompt 顶层组装器。

职责：
- 显式声明 system prompt 的 section 顺序。
- 组织稳定层 / 动态层边界。
- 拼接非空 section 为最终字符串。
"""

from typing import Iterable, Optional

from backend.prompt.sections import (
    get_agent_overlay_section,
    get_available_skills_section,
    get_selected_skill_section,
    get_user_profile_section,
    get_workspace_rules_section,
)
from backend.prompt.types import PromptSection

PROMPT_DYNAMIC_BOUNDARY = "<DYNAMIC_CONTEXT_BOUNDARY>"


def _collect_sections(
    sections: Iterable[Optional[PromptSection]],
) -> list[PromptSection]:
    """过滤掉空 section，保持调用方给定顺序。"""
    return [section for section in sections if section is not None]


def get_dynamic_boundary_section(
    dynamic_sections: Iterable[Optional[PromptSection]],
) -> Optional[PromptSection]:
    """只有存在动态 section 时才显式插入边界。"""
    if not any(section is not None for section in dynamic_sections):
        return None

    return PromptSection(
        key="dynamic_boundary",
        content=PROMPT_DYNAMIC_BOUNDARY,
    )


def build_runtime_system_prompt(
    *,
    available_skills: list,
    selected_skill_content: Optional[str] = None,
    local_rules_text: Optional[str] = None,
    user_profile_text: Optional[str] = None,
    agent_overlay_text: Optional[str] = None,
) -> str:
    """按显式 section 顺序拼装最终 system prompt。"""
    dynamic_sections = [
        get_selected_skill_section(selected_skill_content),
    ]
    sections = _collect_sections(
        [
            # === 1. Stable sections (least likely to change during the conversation) ===
            get_available_skills_section(available_skills),
            get_workspace_rules_section(local_rules_text),
            get_user_profile_section(user_profile_text),
            get_agent_overlay_section(agent_overlay_text),
            # === 2. Dynamic boundary ===
            get_dynamic_boundary_section(dynamic_sections),
            # === 3. Dynamic sections (most likely to change during the conversation) ===
            *dynamic_sections,
        ]
    )
    return "\n\n".join(section.content for section in sections)
