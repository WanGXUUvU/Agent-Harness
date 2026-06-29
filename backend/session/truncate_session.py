"""截断会话历史。"""

from sqlalchemy.orm import Session

from backend.infra.db.orm_models import (
    PendingApproval,
    SessionRunEventRecord,
    SessionRunRecord,
    ToolCallRecord,
)
from backend.session.store import SessionStore


def truncate_session(
    db: Session,
    session_id: str,
    message_index: int,
) -> dict[str, bool]:
    """物理截断指定索引后的消息及级联运行轨迹数据。"""
    store = SessionStore(db)
    record = store.load_record(session_id=session_id)
    if record is None:
        raise ValueError("Session not found")

    state = store.read_session_state(session_id=session_id)
    if state is None:
        raise ValueError("Session state not found")
    if message_index < 0 or message_index >= len(state.messages):
        raise ValueError("Invalid message index")

    try:
        state.messages = state.messages[:message_index]
        store.save_state(
            session_id=session_id,
            state=state,
            session_name=record.session_name,
        )

        top_runs = (
            db.query(SessionRunRecord)
            .filter(
                SessionRunRecord.session_id == session_id,
                SessionRunRecord.parent_run_id.is_(None),
            )
            .order_by(SessionRunRecord.id.asc())
            .all()
        )
        retained_run_count = sum(1 for msg in state.messages if msg.role == "user")
        to_delete = top_runs[retained_run_count:]

        if to_delete:
            run_ids = [record.run_id for record in to_delete]
            db.query(PendingApproval).filter(
                PendingApproval.run_id.in_(run_ids)
            ).delete(synchronize_session=False)
            db.query(ToolCallRecord).filter(
                ToolCallRecord.run_id.in_(run_ids)
            ).delete(synchronize_session=False)
            db.query(SessionRunEventRecord).filter(
                SessionRunEventRecord.run_id.in_(run_ids)
            ).delete(synchronize_session=False)
            db.query(SessionRunRecord).filter(
                SessionRunRecord.run_id.in_(run_ids)
                | SessionRunRecord.parent_run_id.in_(run_ids)
            ).delete(synchronize_session=False)

        db.commit()
    except Exception:
        db.rollback()
        raise

    return {"ok": True}
