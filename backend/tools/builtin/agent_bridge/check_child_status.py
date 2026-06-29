"""构建查询子 Agent 状态的工具定义。"""

from typing import Callable
from backend.tools.result_types import ToolResult
from backend.tools.types import ToolDefinition
from backend.tools.types import RiskLevel
import json


def build_check_child_status_tool(
    status_checker: Callable[[list[str]], dict],
) -> ToolDefinition:
    """构建查询子 Agent 状态的工具定义。"""

    def check_child_status(child_run_ids: str) -> ToolResult:
        """查询一批子 Agent 的状态。"""
        try:
            ids = json.loads(child_run_ids)  # "[\"aaa\",\"bbb\"]" → ["aaa", "bbb"]
        except json.JSONDecodeError as exc:
            return ToolResult(ok=False, content=f"Invalid JSON: {exc}")

        try:
            result = status_checker(ids)
            return ToolResult(ok=True, content=json.dumps(result, ensure_ascii=False))
        except Exception as e:
            return ToolResult(ok=False, content=f"Failed to check status: {e}")

    SCHEMA = {
        "type": "function",
        "function": {
            "name": "check_child_status",
            "description": (
                "非阻塞查询一批子 Agent 的运行状态。"
                "返回每个 child_run_id 对应的状态：running（仍在执行）、done（已完成，reply 字段含最终回复）、error（失败，error 字段含原因）、not_found（id 不存在）。"
                "适合并行场景：先 spawn 多个子任务，再用此工具轮询，处理已完成的同时等待未完成的。"
                "当所有任务均为 done 时，从各条目的 reply 字段提取结果即可，无需再调用 wait_child_agent。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "child_run_ids": {
                        "type": "string",
                        "description": '要查询的子 Agent ID 列表，JSON 数组格式，如 ["id1", "id2"]',
                    },
                },
                "required": ["child_run_ids"],
                "additionalProperties": False,
            },
        },
    }

    return ToolDefinition(
        name="check_child_status",
        schema=SCHEMA,
        handler=check_child_status,
        risk_level=RiskLevel.SAFE,
    )
