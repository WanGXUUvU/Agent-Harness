"""读取会话。"""

from sqlalchemy.orm import Session

from backend.session.store import SessionStore


def read_session(db: Session, session_id: str):
    """返回会话主记录和当前状态快照。"""
    store = SessionStore(db)
    record = store.load_record(session_id=session_id)
    if record is None:
        return None, None
    state = store.read_session_state(session_id=session_id)
    return record, state
