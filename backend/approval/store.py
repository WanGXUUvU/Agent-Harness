"""读写审批记录。"""

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from backend.infra.db.orm_models import PendingApproval
from backend.core.types import ChatMessage


class SqliteApprovalStore:
    """用于审批记录的数据库仓储。"""

    def __init__(self, db: Session):
        """保存数据库会话。"""
        self.db = db

    def create(
        self,
        session_id: str,
        run_id: str,
        batch_id: str,
        tool_name: str,
        tool_call_id: str,
        arguments: str,
        saved_messages: list[ChatMessage],
        event_index: int,
    ) -> PendingApproval:
        """创建一条待审批记录。"""
        record = PendingApproval(
            id=uuid.uuid4().hex,
            session_id=session_id,
            run_id=run_id,
            batch_id=batch_id,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            arguments=arguments,
            status="pending",
            saved_messages=[
                saved_message.model_dump(exclude_none=True)
                for saved_message in saved_messages
            ],
            event_index=event_index,
        )

        self.db.add(record)

        return record

    def get(self, approval_id: str) -> Optional[PendingApproval]:
        """按 ID 读取审批记录。"""
        return (
            self.db.query(PendingApproval)
            .filter(PendingApproval.id == approval_id)
            .first()
        )

    def update_status(self, approval_id: str, status: str) -> Optional[PendingApproval]:
        """更新审批记录状态。"""
        record = self.get(approval_id=approval_id)
        if record is None:
            return None
        record.status = status
        return record

    def restore_messages(self, approval: PendingApproval) -> list[ChatMessage]:
        """恢复审批记录里保存的消息列表。"""
        return [ChatMessage.model_validate(msg) for msg in approval.saved_messages]

    def is_batch_fully_resolved(self, batch_id: str) -> bool:
        """检查某一批 tool_calls 关联的待审批项是否都已经处理完。"""
        pending_count = (
            self.db.query(PendingApproval)
            .filter(PendingApproval.batch_id == batch_id)
            .filter(PendingApproval.status == "pending")
            .count()
        )
        return pending_count == 0

    def get_next_pending_for_batch(self, batch_id: str) -> Optional[PendingApproval]:
        """返回同一批 tool_calls 里下一个待处理的审批单。"""
        return (
            self.db.query(PendingApproval)
            .filter(
                PendingApproval.batch_id == batch_id,
                PendingApproval.status == "pending",
            )
            .order_by(PendingApproval.created_at.asc(), PendingApproval.id.asc())
            .first()
        )

    def get_next_pending_for_run(self, run_id: str) -> Optional[PendingApproval]:
        """返回同一次运行下下一个待处理的审批单。

        仅用于定位当前活跃批次的第一张待处理审批单。
        """
        return (
            self.db.query(PendingApproval)
            .filter(
                PendingApproval.run_id == run_id,
                PendingApproval.status == "pending",
            )
            .order_by(PendingApproval.created_at.asc(), PendingApproval.id.asc())
            .first()
        )
