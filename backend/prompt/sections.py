"""system prompt section 生成器。

职责：
- 把单一来源数据转换为单一 PromptSection。
- 不决定 section 的全局顺序。
- 不负责最终字符串拼接。
"""

from typing import Optional

from backend.prompt.types import PromptSection


def normalize_prompt_text(content: Optional[str]) -> Optional[str]:
    """统一过滤空白内容。"""
    if content is None:
        return None
    normalized = content.strip()
    return normalized or None


def wrap_prompt_section(tag: str, content: str) -> str:
    """用统一标签包裹 section 正文。"""
    return f"<{tag}>\n{content}\n</{tag}>"


def get_available_skills_section(skills: list) -> Optional[PromptSection]:
    """把当前启用的 skills 组装为稳定 section。"""
    enabled_skills = [skill for skill in skills if skill.enabled]
    if not enabled_skills:
        return None

    lines = []
    for skill in enabled_skills:
        description = skill.description or "No description"
        lines.append(f"- {skill.name}: {description}")

    return PromptSection(
        key="available_skills",
        content=wrap_prompt_section("AVAILABLE_SKILLS", "\n".join(lines)),
    )


def get_workspace_rules_section(
    local_rules_text: Optional[str],
) -> Optional[PromptSection]:
    """把工作区 AGENTS.md 规则包成稳定 section。"""
    normalized = normalize_prompt_text(local_rules_text)
    if normalized is None:
        return None

    return PromptSection(
        key="workspace_rules",
        content=wrap_prompt_section("WORKSPACE_RULES", normalized),
    )


def get_user_profile_section(
    user_profile_text: Optional[str],
) -> Optional[PromptSection]:
    """把 USER.md 偏好包成稳定 section。"""
    normalized = normalize_prompt_text(user_profile_text)
    if normalized is None:
        return None

    return PromptSection(
        key="user_profile",
        content=wrap_prompt_section("USER_PROFILE", normalized),
    )


def get_agent_overlay_section(
    agent_overlay_text: Optional[str],
) -> Optional[PromptSection]:
    """把当前 agent 的附加提示词包成稳定 overlay。"""
    normalized = normalize_prompt_text(agent_overlay_text)
    if normalized is None:
        return None

    return PromptSection(
        key="agent_overlay",
        content=wrap_prompt_section("AGENT_OVERLAY", normalized),
    )


def get_selected_skill_section(
    selected_skill_content: Optional[str],
) -> Optional[PromptSection]:
    """把本轮显式选中的 skill 正文包成动态 section。"""
    normalized = normalize_prompt_text(selected_skill_content)
    if normalized is None:
        return None

    return PromptSection(
        key="selected_skill",
        content=wrap_prompt_section("SELECTED_SKILL", normalized),
    )
