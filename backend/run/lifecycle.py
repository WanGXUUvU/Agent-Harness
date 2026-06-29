"""放运行生命周期共用的过程函数。"""

import asyncio
from typing import Any, AsyncIterator, Optional

from sqlalchemy.orm import Session

from backend.core.types import StreamChunk
from backend.run.types import (
    RunFinalStatus,
    RunFinalizationInput,
)
from backend.agent_loop.types import RunEvent
from backend.memory.run.store import RunTraceStore
from backend.approval.store import SqliteApprovalStore
from backend.run.runtime.recorder import RunRecorder


# === 流处理 ================================================================

async def process_agent_stream(
    *,
    raw_stream: AsyncIterator,
    event_index: int = 0,
    initial_events: Optional[list[RunEvent]] = None,
) -> AsyncIterator[dict]:
    """遍历智能体原始生成器流，缓冲文本与 thinking deltas，产出标准 client SSE dict 帧。"""
    thinking_buf = ""
    events: list[RunEvent] = list(initial_events) if initial_events else []
    usage_count = 0

    async def _flush_thinking() -> AsyncIterator[dict]:
        nonlocal thinking_buf
        if thinking_buf.strip():
            event = RunEvent(
                index=len(events) + event_index,
                type="thinking",
                content=thinking_buf,
            )
            events.append(event)
            thinking_buf = ""
            yield {"type": "run_event", "data": event.model_dump()}

    try:
        async for item in raw_stream:
            if isinstance(item, str):
                yield {"type": "delta", "data": {"content": item}}

            elif isinstance(item, StreamChunk) and item.type == "thinking_delta":
                chunk = item.thinking_delta or ""
                thinking_buf += chunk
                yield {"type": "thinking_delta", "data": {"content": chunk}}

            elif isinstance(item, StreamChunk) and item.type == "done" and item.usage:
                usage_count += 1
                yield {
                    "type": "usage",
                    "data": {
                        "model_call_index": usage_count,
                        "usage": item.usage.model_dump(),
                    },
                }

            elif isinstance(item, RunEvent):
                async for flushed in _flush_thinking():
                    yield flushed

                if not item.transient:
                    events.append(item)
                yield {"type": "run_event", "data": item.model_dump()}

        async for flushed in _flush_thinking():
            yield flushed

    except (GeneratorExit, asyncio.CancelledError):
        async for flushed in _flush_thinking():
            yield flushed
        raise
    except Exception:
        async for flushed in _flush_thinking():
            yield flushed
        raise


def persist_run_event(
    *,
    db: Session,
    run_id: str,
    event: RunEvent,
    session_id: str,
    loop_messages: list,
    active_tool_calls: dict,
) -> None:
    """现场进行数据库写入副作用，无须回调。"""
    run_store = RunTraceStore(db)
    approval_store = SqliteApprovalStore(db)

    # 1. 工具开始：创建进行中的调用记录
    if event.type == "assistant_tool_call" and not event.transient:
        record_id = run_store.create_tool_call(
            run_id=run_id,
            tool_name=event.tool_name,
            tool_call_id=event.tool_call_id,
            input_json=event.content,
        )
        db.commit()
        active_tool_calls[event.tool_call_id] = record_id

    # 2. 工具结束：关闭进行中的调用记录
    elif event.type in ("tool_result", "tool_error"):
        record_id = active_tool_calls.pop(event.tool_call_id, None)
        if record_id is not None:
            status = "completed" if event.type == "tool_result" else "failed"
            run_store.finish_tool_call(
                record_id=record_id,
                status=status,
                result_json=event.content,
            )
            db.commit()

    # 3. 需要审批：创建审批检查点
    elif event.type == "approval_required":
        approval_store.create(
            session_id=session_id,
            run_id=run_id,
            batch_id=run_id,
            tool_name=event.tool_name,
            tool_call_id=event.tool_call_id,
            arguments=event.content,
            saved_messages=list(loop_messages),
            event_index=event.index,
        )
        db.commit()


# === 最终收口 ==============================================================

def finalize_run_execution(
    db: Session,
    run_id: str,
    session_id: str,
    user_input: str,
    status: RunFinalStatus,
    events: list[RunEvent],
    reply: str,
    effective_agent_name: Optional[str],
    loop_state: Any,
    last_usage: Optional[Any] = None,
    is_resume: bool = False,
    owns_session: bool = True,
    recorder: Optional[RunRecorder] = None,
) -> None:
    """完成 Run 时调用 recorder 进行最后的状态保存与写入。"""
    rec = recorder or RunRecorder(db)
    final_input = RunFinalizationInput(
        session_id=session_id,
        run_id=run_id,
        status=status,
        user_input=user_input,
        reply=reply,
        agent_name=effective_agent_name,
        events=events,
        state=loop_state,
        usage=last_usage,
        is_resume=is_resume,
        owns_session=owns_session,
    )
    rec.finalize_run(finalization=final_input)
