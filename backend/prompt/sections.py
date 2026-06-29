"""把不同 prompt 物料转成独立 section。"""

from typing import Any, Optional

from backend.prompt.common import wrap_section


def get_available_skills_section(available_skills: list[Any]) -> Optional[str]:
    """构建可用技能区块。"""
    enabled_skills = [skill for skill in available_skills if skill.enabled]
    if not enabled_skills:
        return None
    lines = [
        f"- {skill.name}: {skill.description or 'No description'}"
        for skill in enabled_skills
    ]
    return wrap_section("AVAILABLE_SKILLS", "\n".join(lines))


def get_workspace_rules_section(local_rules_text: Optional[str]) -> Optional[str]:
    """构建 workspace rules section。"""
    if not local_rules_text or not local_rules_text.strip():
        return None
    return wrap_section("WORKSPACE_RULES", local_rules_text)


def get_user_profile_section(user_profile_text: Optional[str]) -> Optional[str]:
    """构建 user profile section。"""
    if not user_profile_text or not user_profile_text.strip():
        return None
    return wrap_section("USER_PROFILE", user_profile_text)


def get_agent_overlay_section(agent_overlay_text: Optional[str]) -> Optional[str]:
    """构建 agent overlay section。"""
    if not agent_overlay_text or not agent_overlay_text.strip():
        return None
    return wrap_section("AGENT_OVERLAY", agent_overlay_text)


def get_selected_skill_section(selected_skill_content: Optional[str]) -> Optional[str]:
    """构建已选技能区块。"""
    if not selected_skill_content or not selected_skill_content.strip():
        return None
    return wrap_section("SELECTED_SKILL", selected_skill_content)
