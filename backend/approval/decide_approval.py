"""审批决策相关动作。"""

from typing import Optional

from sqlalchemy.orm import Session

from backend.approval.store import SqliteApprovalStore
from backend.infra.db.orm_models import PendingApproval, SessionRecord, SessionRunRecord


class ApprovalRunNotPaused(RuntimeError):
    """审批决策前要求对应运行处于暂停状态。"""


def get_approval(db: Session, approval_id: str) -> Optional[PendingApproval]:
    """读取一条审批记录。"""
    return SqliteApprovalStore(db).get(approval_id=approval_id)


def approve_approval(db: Session, approval_id: str) -> Optional[PendingApproval]:
    """同意一条待审批记录。"""
    record = _get_decidable_approval(
        db=db,
        approval_id=approval_id,
    )
    if record is None:
        return None
    record.status = "approved"
    db.commit()
    return record


def reject_approval(db: Session, approval_id: str) -> Optional[PendingApproval]:
    """拒绝一条待审批记录。"""
    record = _get_decidable_approval(
        db=db,
        approval_id=approval_id,
    )
    if record is None:
        return None
    record.status = "rejected"
    db.commit()
    return record


def approve_all_approvals(db: Session, approval_id: str) -> Optional[PendingApproval]:
    """同意一条审批并把会话提升为全自动模式。"""
    record = _get_decidable_approval(
        db=db,
        approval_id=approval_id,
    )
    if record is None:
        return None
    record.status = "approved"
    session_record = (
        db.query(SessionRecord)
        .filter(SessionRecord.session_id == record.session_id)
        .first()
    )
    if session_record:
        session_record.permission_profile = "full-auto"
    db.commit()
    return record


def _get_decidable_approval(
    db: Session,
    approval_id: str,
) -> Optional[PendingApproval]:
    record = SqliteApprovalStore(db).get(approval_id=approval_id)
    if record is None:
        return None

    run_record = (
        db.query(SessionRunRecord)
        .filter(SessionRunRecord.run_id == record.run_id)
        .first()
    )
    if run_record is None or run_record.run_status != "paused":
        raise ApprovalRunNotPaused("Run is not paused yet")
    return record
