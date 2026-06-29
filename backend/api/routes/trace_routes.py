"""定义运行轨迹查询相关 HTTP 路由。"""

from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.api.dto.schemas import TraceResponse, TraceRunSummary
from backend.api.routes.dependencies import error_response
from backend.infra.db.engine import get_db
from backend.run.query_run import load_trace

router = APIRouter()  # 创建路由器


@router.get("/sessions/{session_id}/trace", response_model=TraceResponse)
def read_session_trace_api(
    session_id: str,
    run_id: Optional[str] = None,
    db: Session = Depends(get_db),
) -> TraceResponse:
    """读取会话运行轨迹。"""
    run_records, events_map = load_trace(
        db=db,
        session_id=session_id,
        run_id=run_id,
    )
    if not run_records:
        return error_response(
            status.HTTP_404_NOT_FOUND, "trace_not_found", "Trace not found"
        )

    runs = []
    for run_record in run_records:
        events = events_map.get(run_record.run_id, [])
        runs.append(
            TraceRunSummary(
                run_id=run_record.run_id,
                session_id=run_record.session_id,
                agent_name=run_record.agent_name,
                user_input=run_record.user_input,
                reply=run_record.reply,
                event_count=run_record.event_count,
                created_at=run_record.created_at,
                finished_at=run_record.finished_at,
                is_active=int(run_record.is_active) if run_record.is_active is not None else 1,
                events=events,
            )
        )
    return TraceResponse(
        session_id=session_id,
        runs=runs,
    )
