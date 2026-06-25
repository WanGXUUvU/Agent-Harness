"""技能上下文服务。

职责：
- 列出当前可用技能。
- 按需加载选中 skill 的正文内容。
- 只返回结构化原始数据，不直接拼最终 prompt。
"""

import sys
from typing import Optional, Callable

from backend.context.types import SkillPromptContext
from backend.execution.persistence.types import RunInput
from backend.skills.loader import (
    list_skills as default_list_skills,
    load_skill_content as default_load_skill_content,
)

list_skills = default_list_skills
load_skill_content = default_load_skill_content


class SkillContextService:
    """负责生成运行期技能上下文。"""

    def __init__(
        self,
        list_skills: Optional[Callable] = None,
        load_skill_content: Optional[Callable[[str], Optional[str]]] = None,
    ):
        """通过依赖注入接收技能目录和 skill 正文加载器。"""
        module = sys.modules[__name__]
        self._list_skills = list_skills or getattr(
            module, "list_skills", default_list_skills
        )
        self._load_skill_content = load_skill_content or getattr(
            module,
            "load_skill_content",
            default_load_skill_content,
        )

    def _get_selected_skill_or_raise(self, skill_name: str, skills: list) -> object:
        """返回已启用的目标技能；找不到或禁用则抛错。"""
        selected_skill = next(
            (skill for skill in skills if skill.name == skill_name),
            None,
        )

        if selected_skill is None:
            raise ValueError(f"Skill not found: {skill_name}")

        if not selected_skill.enabled:
            raise ValueError(f"Skill is disabled: {skill_name}")

        return selected_skill

    def build_prompt_context(self, run_input: RunInput) -> SkillPromptContext:
        """返回 skill 目录与当前选中 skill 正文。"""
        skills = self._list_skills()
        selected_skill_content = None

        if run_input.skill_name:
            self._get_selected_skill_or_raise(run_input.skill_name, skills)
            selected_skill_content = self._load_skill_content(run_input.skill_name)

        return SkillPromptContext(
            skills=skills,
            selected_skill_content=selected_skill_content,
        )
