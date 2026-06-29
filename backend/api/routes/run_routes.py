"""定义运行相关的 HTTP 路由。"""

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.api.dto.schemas import RunDetailResponse, ToolCallSummary
from backend.api.routes.dependencies import error_response
from backend.infra.db.engine import get_db
from backend.run.cancel_run import cancel_run
from backend.run.execute_run_stream import execute_run_stream
from backend.run.execute_run_sync import execute_run_sync
from backend.run.query_run import get_child_run_status, load_run_detail
from backend.run.types import (
    RunInput,
    RunOutput,
    FinalizeRunInput,
)
from backend.session.reset_session import reset_session
from backend.session.types import ResetInput

router = APIRouter()  # 创建本文件路由器


@router.post("/run", response_model=RunOutput)
def run_agent_api(
    run_input: RunInput,
    db: Session = Depends(get_db),
) -> RunOutput:
    """执行非流式运行。"""
    try:
        return execute_run_sync(
            db=db,
            run_input=run_input,
        )
    except ValueError as exc:
        return error_response(status.HTTP_400_BAD_REQUEST, "bad_request", str(exc))


@router.post("/reset")
def reset_session_api(
    payload: ResetInput,
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    """重置会话状态。"""
    try:
        return reset_session(
            db=db,
            payload=payload,
        )
    except ValueError as exc:
        return error_response(status.HTTP_400_BAD_REQUEST, "bad_request", str(exc))


@router.post("/run/stream")
async def run_stream_api(
    run_input: RunInput,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """执行流式运行。"""
    try:
        return StreamingResponse(
            execute_run_stream(
                db=db,
                run_input=run_input,
            ),
            media_type="text/event-stream",
        )
    except ValueError as exc:
        return error_response(status.HTTP_400_BAD_REQUEST, "bad request", str(exc))


@router.post("/sessions/{session_id}/runs/{run_id}/finalize")
def cancel_run_api(
    session_id: str,
    run_id: str,
    payload: FinalizeRunInput,
    db: Session = Depends(get_db),
):
    """手动收口一次运行记录。"""
    try:
        return cancel_run(
            db=db,
            session_id=session_id,
            run_id=run_id,
            user_input=payload.user_input,
            reply=payload.reply,
            agent_name=payload.agent_name,
        )
    except ValueError as exc:
        return error_response(status.HTTP_400_BAD_REQUEST, "bad_request", str(exc))


@router.get("/sessions/{session_id}/runs/{run_id}")
def get_run_detail_api(
    session_id: str,
    run_id: str,
    db: Session = Depends(get_db),
):
    """读取单次运行详情。"""
    run, tool_calls = load_run_detail(
        db=db,
        session_id=session_id,
        run_id=run_id,
    )
    if not run:
        return error_response(status.HTTP_404_NOT_FOUND, "not found", "run not found")
    return RunDetailResponse(
        run_id=run.run_id,
        session_id=run.session_id,
        run_status=run.run_status,
        user_input=run.user_input,
        reply=run.reply,
        agent_name=run.agent_name,
        created_at=run.created_at,
        tool_calls=[
            ToolCallSummary(
                id=tc.id,
                tool_name=tc.tool_name,
                tool_call_id=tc.tool_call_id,
                status=tc.status,
                input_json=tc.input_json,
                result_json=tc.result_json,
                started_at=tc.started_at,
                finished_at=tc.finished_at,
            )
            for tc in tool_calls
        ],
    )


@router.get("/child-runs/{run_id}")
def get_child_run_status_api(
    run_id: str,
):
    """查询子 Agent 运行状态。"""
    return get_child_run_status(run_id=run_id)
