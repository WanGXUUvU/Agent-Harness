"""删除会话。"""

from sqlalchemy.orm import Session

from backend.session.store import SessionStore


def delete_session(db: Session, session_id: str) -> dict[str, bool]:
    """删除会话及其关联运行数据。"""
    store = SessionStore(db)
    record = store.load_record(session_id=session_id)
    if record is None:
        raise ValueError("Session not found")

    try:
        store.delete_session(session_id=session_id)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {"ok": True}
