"""技能管理相关动作。"""

from backend.skills.loader import (
    list_skills as load_skill_summaries,
    load_skill_config,
    save_skill_config,
)
from backend.skills.types import SkillSummary


def list_available_skills() -> list[SkillSummary]:
    """返回可见技能列表。"""
    return load_skill_summaries()


def enable_skill(skill_name: str) -> SkillSummary:
    """启用一个已有技能。"""
    _require_skill(skill_name)

    config = load_skill_config()
    config.disabled.discard(skill_name)
    save_skill_config(config)
    return _reload_skill(skill_name)


def disable_skill(skill_name: str) -> SkillSummary:
    """禁用一个已有技能。"""
    _require_skill(skill_name)

    config = load_skill_config()
    config.disabled.add(skill_name)
    save_skill_config(config)
    return _reload_skill(skill_name)


def _require_skill(skill_name: str) -> SkillSummary:
    for skill in list_available_skills():
        if skill.name == skill_name:
            return skill
    raise ValueError(f"Skill not found: {skill_name}")


def _reload_skill(skill_name: str) -> SkillSummary:
    for skill in list_available_skills():
        if skill.name == skill_name:
            return skill
    raise ValueError(f"Skill not found: {skill_name}")
