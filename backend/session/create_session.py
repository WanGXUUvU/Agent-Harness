"""创建会话。"""

import uuid

from sqlalchemy.orm import Session

from backend.agent_loop.types import RunState
from backend.infra.db.orm_models import ModelSetting, ProviderConfig
from backend.session.build_session_summary import build_session_summary
from backend.session.store import SessionStore
from backend.session.types import CreateSessionInput, SessionSummary


def create_session(db: Session, payload: CreateSessionInput) -> SessionSummary:
    """创建带默认服务商和模型绑定的新空会话。"""
    session_id = uuid.uuid4().hex
    state = RunState()
    store = SessionStore(db)

    default_provider = (
        db.query(ProviderConfig).filter(ProviderConfig.is_default == 1).first()
    )
    default_provider_id = None
    default_model_id = None

    if default_provider:
        default_model = (
            db.query(ModelSetting)
            .filter(
                ModelSetting.provider_id == default_provider.id,
                ModelSetting.enabled == 1,
            )
            .first()
        )
        default_provider_id = default_provider.id
        default_model_id = default_model.model_id if default_model else None

    try:
        record = store.save_state(
            session_id=session_id,
            state=state,
            session_name=payload.session_name,
            last_agent_name=None,
            last_reply_preview=None,
            workspace_path=payload.workspace_path,
            workspace_name=payload.workspace_name,
        )
        record.model_provider_id = default_provider_id
        record.model_id = default_model_id
        db.commit()
        db.refresh(record)
    except Exception:
        db.rollback()
        raise

    return build_session_summary(record=record)
