"""执行同步单轮运行并持久化结果。"""

import uuid
from sqlalchemy.orm import Session

from backend.run.types import RunInput, RunOutput, RunFinalStatus
from backend.run.runtime.vfs import RunVfsRegistry
from backend.run.setup import build_run_setup
from backend.run.build_agent_loop import build_agent_loop
from backend.run.lifecycle import persist_run_event, finalize_run_execution


def execute_run_sync(*, db: Session, run_input: RunInput) -> RunOutput:
    """执行一次同步运行，并在结束后持久化结果。"""
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

        # 3. 执行同步单轮 Agent
        output = loop.run_sync(
            run_input=run_input,
            run_id=run_id,
        )

        # 4. 持久化产出的事件
        active_tool_calls = {}
        for event in output.events:
            persist_run_event(
                db=db,
                run_id=run_id,
                event=event,
                session_id=run_input.session_id,
                loop_messages=loop.state.messages,
                active_tool_calls=active_tool_calls,
            )

        # 5. 收口最终状态与元数据
        finalize_run_execution(
            db=db,
            run_id=run_id,
            session_id=run_input.session_id,
            user_input=run_input.user_input,
            status=RunFinalStatus.COMPLETED,
            events=output.events,
            reply=output.reply,
            effective_agent_name=run_setup.effective_agent_name,
            loop_state=loop.state,
            last_usage=getattr(loop, "last_usage", None),
        )

        output.metadata.run_id = run_id
        output.metadata.agent_name = run_setup.effective_agent_name
        return output
    except Exception:
        # 最终收口前失败：只清理本轮 VFS 作用域
        RunVfsRegistry.discard(run_id)
        raise
