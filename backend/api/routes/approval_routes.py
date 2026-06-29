"""定义审批相关的 HTTP 路由。"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.approval import (
    ApprovalRunNotPaused,
    approve_all_approvals,
    approve_approval,
    get_approval,
    reject_approval,
)
from backend.infra.db.engine import get_db
from backend.run.execute_run_resume import execute_run_resume

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("/{approval_id}")
def get_approval_api(
    approval_id: str,
    db: Session = Depends(get_db),
):
    """读取单条审批记录。"""
    record = get_approval(
        db=db,
        approval_id=approval_id,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return record


@router.post("/{approval_id}/approve")
async def approve(
    approval_id: str,
    db: Session = Depends(get_db),
):
    """同意审批并恢复运行。"""
    try:
        record = approve_approval(
            db=db,
            approval_id=approval_id,
        )
    except ApprovalRunNotPaused as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return StreamingResponse(
        execute_run_resume(
            db=db,
            approval_id=approval_id,
            rejected=False,
        ),
        media_type="text/event-stream",
    )


@router.post("/{approval_id}/reject")
async def reject(
    approval_id: str,
    db: Session = Depends(get_db),
):
    """拒绝审批并恢复运行。"""
    try:
        record = reject_approval(
            db=db,
            approval_id=approval_id,
        )
    except ApprovalRunNotPaused as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return StreamingResponse(
        execute_run_resume(
            db=db,
            approval_id=approval_id,
            rejected=True,
        ),
        media_type="text/event-stream",
    )


@router.post("/{approval_id}/approve_all")
async def approve_all(
    approval_id: str,
    db: Session = Depends(get_db),
):
    """同意当前批次后续全部审批并恢复运行。"""
    try:
        record = approve_all_approvals(
            db=db,
            approval_id=approval_id,
        )
    except ApprovalRunNotPaused as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return StreamingResponse(
        execute_run_resume(
            db=db,
            approval_id=approval_id,
            rejected=False,
        ),
        media_type="text/event-stream",
    )
