"""构建会话摘要数据对象。"""

from backend.infra.db.orm_models import SessionRecord
from backend.session.types import SessionSummary


def build_session_summary(record: SessionRecord) -> SessionSummary:
    """把会话 ORM 记录映射成领域摘要对象。"""
    return SessionSummary(
        session_id=record.session_id,
        session_name=record.session_name,
        created_at=record.created_at,
        updated_at=record.updated_at,
        last_agent_name=record.last_agent_name,
        message_count=record.message_count,
        last_reply_preview=record.last_reply_preview,
        permission_profile=record.permission_profile,
        context_tokens=record.context_tokens,
        workspace_path=record.workspace_path,
        workspace_name=record.workspace_name,
        parent_session_id=record.parent_session_id,
        fork_message_index=record.fork_message_index,
    )
