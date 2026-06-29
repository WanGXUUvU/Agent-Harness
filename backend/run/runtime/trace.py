"""读取运行轨迹数据。"""

import json
from typing import Optional

from backend.agent_loop.types import RunEvent
from backend.memory.run.store import RunTraceStore
from backend.tools.result_types import ToolResult


def load_session_trace(
    run_store: RunTraceStore,
    session_id: str,
    run_id: Optional[str] = None,
):
    """返回指定会话的运行记录和事件映射。"""
    run_records = run_store.list_run_records(session_id, run_id=run_id)
    if not run_records:
        return [], {}

    events_map: dict[str, list[RunEvent]] = {}
    for run_record in run_records:
        event_rows = run_store.list_run_events(run_record.run_id)
        events = []
        for row in event_rows:
            tool_result = None
            if row.tool_result_json:
                tool_result = ToolResult.model_validate(
                    json.loads(row.tool_result_json)
                )
            events.append(
                RunEvent(
                    index=row.event_index,
                    type=row.type,
                    content=row.content,
                    tool_name=row.tool_name,
                    tool_call_id=row.tool_call_id,
                    tool_result=tool_result,
                )
            )
        events_map[run_record.run_id] = events

    return run_records, events_map
