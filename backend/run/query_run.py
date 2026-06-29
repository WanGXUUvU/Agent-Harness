"""查询历史 Traces 与子 Agent 执行状态的执行逻辑。"""

from typing import Optional
from sqlalchemy.orm import Session

from backend.memory.run.store import RunTraceStore
from backend.run.runtime.trace import load_session_trace
from backend.run.child.launcher import get_child_run_status as fetch_child_status


def load_run_detail(db: Session, session_id: str, run_id: str):
    """返回某次运行的回复和工具调用详情。"""
    run, tool_calls = RunTraceStore(db).get_run_detail(run_id=run_id)
    if not run or run.session_id != session_id:
        return None, []
    return run, tool_calls


def get_child_run_status(run_id: str) -> dict:
    """查询单个子 Agent 的运行状态。"""
    return fetch_child_status(run_id=run_id)


def load_trace(db: Session, session_id: str, run_id: Optional[str] = None):
    """读取会话轨迹；可按运行 ID 过滤。"""
    return load_session_trace(
        run_store=RunTraceStore(db),
        session_id=session_id,
        run_id=run_id,
    )
