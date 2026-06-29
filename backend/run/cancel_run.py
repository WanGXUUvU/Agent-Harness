"""终止或归档已中断运行的执行逻辑。"""

from typing import Optional
from sqlalchemy.orm import Session

from backend.session.store import SessionStore
from backend.agent_loop.types import RunState
from backend.run.runtime.recorder import RunRecorder
from backend.run.types import RunFinalizationInput, RunFinalStatus


def cancel_run(
    db: Session,
    session_id: str,
    run_id: str,
    user_input: str,
    reply: str,
    agent_name: Optional[str],
) -> dict:
    """保存被中止 run 的当前状态。"""
    state = SessionStore(db).get(session_id) or RunState()
    RunRecorder(db).finalize_run(
        RunFinalizationInput(
            session_id=session_id,
            run_id=run_id,
            status=RunFinalStatus.CANCELLED,
            user_input=user_input,
            reply=reply,
            agent_name=agent_name,
            state=state,
        )
    )
    return {"ok": True}
