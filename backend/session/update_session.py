"""更新会话。"""

from sqlalchemy.orm import Session

from backend.session.store import SessionStore
from backend.session.types import RenameSessionInput


def update_session(
    db: Session,
    session_id: str,
    payload: RenameSessionInput,
) -> dict[str, bool]:
    """更新可变会话字段。"""
    store = SessionStore(db)
    record = store.load_record(session_id=session_id)
    if record is None:
        raise ValueError("Session not found")

    try:
        if payload.session_name is not None:
            if not payload.session_name.strip():
                raise ValueError("Session name cannot be empty")
            store.rename_session(
                session_id=session_id,
                new_name=payload.session_name,
            )
        if payload.permission_profile is not None:
            record.permission_profile = payload.permission_profile
        if payload.model_id is not None:
            record.model_id = payload.model_id
        if payload.model_provider_id is not None:
            record.model_provider_id = payload.model_provider_id
        if payload.thinking_enabled is not None:
            record.thinking_enabled = 1 if payload.thinking_enabled else 0
        if payload.thinking_effort is not None:
            record.thinking_effort = payload.thinking_effort
        if payload.workspace_path is not None:
            record.workspace_path = payload.workspace_path
        if payload.workspace_name is not None:
            record.workspace_name = payload.workspace_name
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {"ok": True}
