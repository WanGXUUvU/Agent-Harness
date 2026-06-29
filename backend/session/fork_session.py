"""分叉会话。"""

import uuid

from sqlalchemy.orm import Session

from backend.agent_loop.types import RunState
from backend.infra.db.orm_models import (
    SessionRunEventRecord,
    SessionRunRecord,
    ToolCallRecord,
)
from backend.session.build_session_summary import build_session_summary
from backend.session.store import SessionStore
from backend.session.types import ForkSessionInput, SessionSummary


def fork_session(
    db: Session,
    session_id: str,
    payload: ForkSessionInput,
) -> SessionSummary:
    """从消息边界创建分支会话并复制运行与轨迹。"""
    store = SessionStore(db)
    parent_record = store.load_record(session_id=session_id)
    if parent_record is None:
        raise ValueError("Parent session not found")

    parent_state = store.read_session_state(session_id=session_id)
    if parent_state is None:
        raise ValueError("Parent session state not found")

    message_index = payload.message_index
    if message_index < 0 or message_index > len(parent_state.messages):
        raise ValueError("Invalid message index")

    forked_messages = parent_state.messages[:message_index]
    forked_state = RunState()
    forked_state.messages = forked_messages
    forked_name = getattr(
        payload,
        "session_name",
        None,
    ) or f"fork: {parent_record.session_name or 'Untitled'}"
    forked_session_id = uuid.uuid4().hex

    try:
        record = store.save_state(
            session_id=forked_session_id,
            state=forked_state,
            session_name=forked_name,
            last_agent_name=parent_record.last_agent_name,
            workspace_path=parent_record.workspace_path,
            workspace_name=parent_record.workspace_name,
        )
        record.model_provider_id = parent_record.model_provider_id
        record.model_id = parent_record.model_id
        record.thinking_enabled = parent_record.thinking_enabled
        record.thinking_effort = parent_record.thinking_effort
        record.permission_profile = parent_record.permission_profile
        record.parent_session_id = session_id
        record.fork_message_index = message_index
        db.flush()

        top_runs = (
            db.query(SessionRunRecord)
            .filter(
                SessionRunRecord.session_id == session_id,
                SessionRunRecord.parent_run_id.is_(None),
            )
            .order_by(SessionRunRecord.id.asc())
            .all()
        )
        retained_run_count = sum(1 for msg in forked_messages if msg.role == "user")
        runs_to_clone = top_runs[:retained_run_count]

        for parent_run in runs_to_clone:
            new_run_id = f"run_{uuid.uuid4().hex[:12]}"
            forked_run = SessionRunRecord(
                session_id=forked_session_id,
                run_id=new_run_id,
                parent_run_id=None,
                run_status=parent_run.run_status,
                agent_name=parent_run.agent_name,
                user_input=parent_run.user_input,
                reply=parent_run.reply,
                event_count=parent_run.event_count,
                created_at=parent_run.created_at,
                finished_at=parent_run.finished_at,
                is_active=parent_run.is_active,
            )
            db.add(forked_run)

            for event in (
                db.query(SessionRunEventRecord)
                .filter(SessionRunEventRecord.run_id == parent_run.run_id)
                .all()
            ):
                db.add(
                    SessionRunEventRecord(
                        run_id=new_run_id,
                        event_index=event.event_index,
                        type=event.type,
                        content=event.content,
                        tool_name=event.tool_name,
                        tool_call_id=event.tool_call_id,
                        tool_result_json=event.tool_result_json,
                    )
                )

            for tool_call in (
                db.query(ToolCallRecord)
                .filter(ToolCallRecord.run_id == parent_run.run_id)
                .all()
            ):
                db.add(
                    ToolCallRecord(
                        run_id=new_run_id,
                        tool_name=tool_call.tool_name,
                        tool_call_id=tool_call.tool_call_id,
                        status=tool_call.status,
                        input_json=tool_call.input_json,
                        result_json=tool_call.result_json,
                        started_at=tool_call.started_at,
                        finished_at=tool_call.finished_at,
                    )
                )

            child_runs = (
                db.query(SessionRunRecord)
                .filter(SessionRunRecord.parent_run_id == parent_run.run_id)
                .all()
            )
            for child_run in child_runs:
                child_new_run_id = f"run_{uuid.uuid4().hex[:12]}"
                db.add(
                    SessionRunRecord(
                        session_id=forked_session_id,
                        run_id=child_new_run_id,
                        parent_run_id=new_run_id,
                        run_status=child_run.run_status,
                        agent_name=child_run.agent_name,
                        user_input=child_run.user_input,
                        reply=child_run.reply,
                        event_count=child_run.event_count,
                        created_at=child_run.created_at,
                        finished_at=child_run.finished_at,
                        is_active=child_run.is_active,
                    )
                )

                for event in (
                    db.query(SessionRunEventRecord)
                    .filter(SessionRunEventRecord.run_id == child_run.run_id)
                    .all()
                ):
                    db.add(
                        SessionRunEventRecord(
                            run_id=child_new_run_id,
                            event_index=event.event_index,
                            type=event.type,
                            content=event.content,
                            tool_name=event.tool_name,
                            tool_call_id=event.tool_call_id,
                            tool_result_json=event.tool_result_json,
                        )
                    )

                for tool_call in (
                    db.query(ToolCallRecord)
                    .filter(ToolCallRecord.run_id == child_run.run_id)
                    .all()
                ):
                    db.add(
                        ToolCallRecord(
                            run_id=child_new_run_id,
                            tool_name=tool_call.tool_name,
                            tool_call_id=tool_call.tool_call_id,
                            status=tool_call.status,
                            input_json=tool_call.input_json,
                            result_json=tool_call.result_json,
                            started_at=tool_call.started_at,
                            finished_at=tool_call.finished_at,
                        )
                    )

        db.commit()
        db.refresh(record)
    except Exception:
        db.rollback()
        raise

    return build_session_summary(record=record)
