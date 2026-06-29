"""定义会话相关 HTTP 路由。"""

import os

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.api.dto.schemas import SessionDetail
from backend.api.routes.dependencies import error_response
from backend.infra.db.engine import get_db
from backend.session import (
    CreateSessionInput,
    ForkSessionInput,
    RenameSessionInput,
    SessionSummary,
    TruncateSessionInput,
    create_session,
    delete_session,
    fork_session,
    list_sessions,
    read_session,
    truncate_session,
    update_session,
)

router = APIRouter()


@router.post("/sessions", response_model=SessionSummary)
def create_session_api(
    payload: CreateSessionInput,
    db: Session = Depends(get_db),
) -> SessionSummary:
    """创建新会话。"""
    return create_session(
        db=db,
        payload=payload,
    )


@router.post("/sessions/{session_id}/fork", response_model=SessionSummary)
def fork_session_api(
    session_id: str,
    payload: ForkSessionInput,
    db: Session = Depends(get_db),
) -> SessionSummary:
    """从指定消息位置派生分支会话。"""
    try:
        return fork_session(
            db=db,
            session_id=session_id,
            payload=payload,
        )
    except ValueError as exc:
        return error_response(status.HTTP_400_BAD_REQUEST, "bad_request", str(exc))


@router.post("/sessions/{session_id}/truncate")
def truncate_session_api(
    session_id: str,
    payload: TruncateSessionInput,
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    """截断指定会话后续历史。"""
    try:
        return truncate_session(
            db=db,
            session_id=session_id,
            message_index=payload.message_index,
        )
    except ValueError as exc:
        return error_response(status.HTTP_400_BAD_REQUEST, "bad_request", str(exc))


@router.delete("/sessions/{session_id}")
def delete_session_api(
    session_id: str,
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    """删除会话。"""
    try:
        return delete_session(
            db=db,
            session_id=session_id,
        )
    except ValueError as exc:
        return error_response(status.HTTP_400_BAD_REQUEST, "bad_request", str(exc))


@router.get("/sessions", response_model=list[SessionSummary])
def list_sessions_api(
    db: Session = Depends(get_db),
) -> list[SessionSummary]:
    """列出所有会话摘要。"""
    return list_sessions(db=db)


@router.get("/sessions/{session_id}", response_model=SessionDetail)
def read_session_api(
    session_id: str,
    db: Session = Depends(get_db),
) -> SessionDetail:
    """读取单个会话详情。"""
    record, state = read_session(
        db=db,
        session_id=session_id,
    )
    if record is None or state is None:
        return error_response(
            status.HTTP_404_NOT_FOUND, "session_not_found", "Session not found"
        )

    workspace_exists = True
    if record.workspace_path:
        workspace_exists = os.path.exists(record.workspace_path)

    return SessionDetail(
        session_id=record.session_id,
        session_name=record.session_name,
        created_at=record.created_at,
        updated_at=record.updated_at,
        last_agent_name=record.last_agent_name,
        last_reply_preview=record.last_reply_preview,
        message_count=record.message_count,
        state=state,
        permission_profile=record.permission_profile,
        model_id=record.model_id,
        model_provider_id=record.model_provider_id,
        thinking_enabled=bool(record.thinking_enabled),
        thinking_effort=record.thinking_effort or "medium",
        workspace_path=record.workspace_path,
        workspace_name=record.workspace_name,
        workspace_exists=workspace_exists,
    )


@router.patch("/sessions/{session_id}")
def rename_session_api(
    session_id: str,
    payload: RenameSessionInput,
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    """更新会话属性。"""
    try:
        return update_session(
            db=db,
            session_id=session_id,
            payload=payload,
        )
    except ValueError as exc:
        return error_response(status.HTTP_400_BAD_REQUEST, "bad_request", str(exc))
