"""列出会话。"""

from sqlalchemy.orm import Session

from backend.session.build_session_summary import build_session_summary
from backend.session.store import SessionStore
from backend.session.types import SessionSummary


def list_sessions(db: Session) -> list[SessionSummary]:
    """按侧边栏顺序返回所有会话。"""
    return [
        build_session_summary(record=record)
        for record in SessionStore(db).list_sessions()
    ]
