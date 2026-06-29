"""收集构建 prompt 需要的原始物料。"""

import logging
import os
from pathlib import Path
from typing import Any, List, Optional

from backend.skills.loader import (
    list_skills as default_list_skills,
    load_skill_content as default_load_skill_content,
)

logger = logging.getLogger(__name__)


def collect_prompt_materials(
    *,
    skill_name: Optional[str],
    workspace_path: Optional[str],
    list_skills_fn=None,
    load_skill_content_fn=None,
) -> dict:
    """收集一次运行所需的全部提示词物料。"""
    list_fn = list_skills_fn or default_list_skills
    load_fn = load_skill_content_fn or default_load_skill_content

    available_skills = list_fn()
    selected_skill_content = _load_selected_skill_content(
        skill_name=skill_name,
        skills=available_skills,
        load_skill_content_fn=load_fn,
    )
    local_rules_text = _read_workspace_file(workspace_path, "AGENTS.md")
    user_profile_text = _read_workspace_file(workspace_path, "USER.md")

    return {
        "available_skills": available_skills,
        "selected_skill_content": selected_skill_content,
        "local_rules_text": local_rules_text,
        "user_profile_text": user_profile_text,
    }


def _load_selected_skill_content(
    *,
    skill_name: Optional[str],
    skills: List[Any],
    load_skill_content_fn,
) -> Optional[str]:
    """按技能名加载被选中技能的完整正文。"""
    if not skill_name:
        return None
    selected_skill = next((s for s in skills if s.name == skill_name), None)
    if selected_skill is None:
        raise ValueError(f"Skill not found: {skill_name}")
    if not selected_skill.enabled:
        raise ValueError(f"Skill is disabled: {skill_name}")
    return load_skill_content_fn(skill_name)


def _read_workspace_file(workspace_path: Optional[str], filename: str) -> Optional[str]:
    """读取工作区下指定文件并 strip；不存在或为空时返回 None。"""
    if not workspace_path or not os.path.exists(workspace_path):
        return None
    path = Path(workspace_path).resolve() / filename
    if not path.exists():
        return None
    try:
        content = path.read_text(encoding="utf-8").strip()
        return content or None
    except Exception:
        logger.warning("Failed to read %s", path, exc_info=True)
        return None
