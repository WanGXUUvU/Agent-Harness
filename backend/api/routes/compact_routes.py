"""定义上下文压缩相关 HTTP 路由。"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.context.compaction import CompactInput, CompactOutput, CompactService
from backend.api.routes.dependencies import error_response
from backend.infra.db.engine import get_db

router = APIRouter()


@router.post("/compact", response_model=CompactOutput)
def compact_session_api(
    payload: CompactInput,
    db: Session = Depends(get_db),
) -> CompactOutput:
    """手动触发会话压缩。"""
    try:
        return CompactService(db).compact_session(payload=payload)
    except ValueError as exc:
        return error_response(status.HTTP_400_BAD_REQUEST, "bad_request", str(exc))
