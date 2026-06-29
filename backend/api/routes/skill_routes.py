"""技能管理 HTTP 路由适配层。"""

from fastapi import APIRouter, status

from backend.skills.types import SkillSummary
from backend.skills.manage_skills import (
    list_available_skills,
    disable_skill,
    enable_skill,
)
from backend.api.routes.dependencies import error_response

router = APIRouter()


@router.get("/skills", response_model=list[SkillSummary])
def list_skills_api() -> list[SkillSummary]:
    """列出可用技能。"""
    return list_available_skills()


@router.post("/skills/{skill_name}/disable", response_model=SkillSummary)
def disable_skill_api(skill_name: str) -> SkillSummary:
    """禁用指定技能。"""
    try:
        return disable_skill(skill_name=skill_name)
    except ValueError as exc:
        return error_response(status.HTTP_400_BAD_REQUEST, "bad_request", str(exc))


@router.post("/skills/{skill_name}/enable", response_model=SkillSummary)
def enable_skill_api(skill_name: str) -> SkillSummary:
    """启用指定技能。"""
    try:
        return enable_skill(skill_name=skill_name)
    except ValueError as exc:
        return error_response(status.HTTP_400_BAD_REQUEST, "bad_request", str(exc))
