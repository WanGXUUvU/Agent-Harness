"""执行流式单轮运行并产出 SSE。"""

import asyncio
import uuid
from typing import AsyncIterator
from sqlalchemy.orm import Session

from backend.run.types import RunInput, RunFinalStatus
from backend.run.runtime.vfs import RunVfsRegistry
from backend.run.setup import build_run_setup
from backend.run.build_agent_loop import build_agent_loop
from backend.run.lifecycle import (
    process_agent_stream,
    persist_run_event,
    finalize_run_execution,
)
from backend.agent_loop.types import RunEvent
from backend.run.runtime.sse import _sse_frame


async def execute_run_stream(
    *,
    db: Session,
    run_input: RunInput,
) -> AsyncIterator[str]:
    """执行一次流式运行并逐帧产出 SSE 数据。"""
    # 1. 打开本轮 run 作用域
    run_id = uuid.uuid4().hex
    RunVfsRegistry.create(run_id)

    try:
        # 2. 构建稳定运行依赖
        run_setup = build_run_setup(
            db=db,
            run_input=run_input,
        )
        loop = build_agent_loop(
            run_id=run_id,
            session_id=run_input.session_id,
            state=run_setup.state,
            agent_profile=run_setup.agent_profile,
            runtime_system_prompt=run_setup.runtime_system_prompt,
            model_adapter=run_setup.adapter,
            approval_policy=run_setup.approval_policy,
        )

        # 3. 启动客户端流
        yield _sse_frame("start", {"run_id": run_id})

        raw_stream = loop.stream(
            run_input=run_input,
            run_id=run_id,
            workspace_path=run_setup.workspace_path,
        )

        reply_text = ""
        events = []
        active_tool_calls = {}

        try:
            # 4. 转发流式帧并持久化可落库事件
            async for frame in process_agent_stream(raw_stream=raw_stream):
                if frame["type"] == "run_event":
                    event = RunEvent(**frame["data"])
                    persist_run_event(
                        db=db,
                        run_id=run_id,
                        event=event,
                        session_id=run_input.session_id,
                        loop_messages=loop.state.messages,
                        active_tool_calls=active_tool_calls,
                    )
                    if not event.transient:
                        events.append(event)
                elif frame["type"] == "delta":
                    reply_text += frame["data"]["content"]

                yield _sse_frame(frame["type"], frame["data"])

            # 5. 收口流式运行状态
            status = (
                RunFinalStatus.PAUSED
                if any(e.type == "approval_required" for e in events)
                else RunFinalStatus.COMPLETED
            )

            finalize_run_execution(
                db=db,
                run_id=run_id,
                session_id=run_input.session_id,
                user_input=run_input.user_input,
                status=status,
                events=events,
                reply=reply_text,
                effective_agent_name=run_setup.effective_agent_name,
                loop_state=loop.state,
                last_usage=getattr(loop, "last_usage", None),
            )

            if status == RunFinalStatus.PAUSED:
                yield _sse_frame("paused", {"run_id": run_id})
            else:
                yield _sse_frame("end", {"state": loop.state.model_dump()})

        except (GeneratorExit, asyncio.CancelledError):
            # Client interrupted after stream started
            finalize_run_execution(
                db=db,
                run_id=run_id,
                session_id=run_input.session_id,
                user_input=run_input.user_input,
                status=RunFinalStatus.CANCELLED,
                events=events,
                reply=reply_text,
                effective_agent_name=run_setup.effective_agent_name,
                loop_state=loop.state,
                last_usage=getattr(loop, "last_usage", None),
            )
            raise
        except Exception:
            # Runtime failed after stream started
            finalize_run_execution(
                db=db,
                run_id=run_id,
                session_id=run_input.session_id,
                user_input=run_input.user_input,
                status=RunFinalStatus.FAILED,
                events=events,
                reply=reply_text,
                effective_agent_name=run_setup.effective_agent_name,
                loop_state=loop.state,
                last_usage=getattr(loop, "last_usage", None),
            )
            raise

    except Exception as e:
        # Failure before durable finalization: discard VFS and surface error frame
        RunVfsRegistry.discard(run_id)
        yield _sse_frame("error", {"message": str(e)})
        raise
