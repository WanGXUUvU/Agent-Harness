"""重置会话。"""

from sqlalchemy.orm import Session

from backend.agent_loop.types import RunState
from backend.session.store import SessionStore
from backend.session.types import ResetInput


def reset_session(db: Session, payload: ResetInput) -> dict[str, bool]:
    """清空状态快照并把现有顶层运行标记为非活跃。"""
    store = SessionStore(db)
    record = store.load_record(session_id=payload.session_id)
    if record is None:
        raise ValueError("Session not found")

    try:
        store.save_state(
            session_id=payload.session_id,
            state=RunState(),
            session_name=record.session_name,
            last_agent_name=None,
            last_reply_preview=None,
        )
        store.reset_session_runs(session_id=payload.session_id)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {"ok": True}
