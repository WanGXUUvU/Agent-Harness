"""构建派发子 Agent 的工具定义。"""

from typing import Callable
from backend.tools.types import ToolDefinition
from backend.tools.result_types import ToolResult
from backend.tools.types import RiskLevel


def build_spawn_child_agent_tool(
    child_dispatcher: Callable[[str, str], str],
) -> ToolDefinition:
    """构建派发子 Agent 的工具定义。"""

    def spawn_child_agent(task: str, agent_name: str = "子Agent") -> ToolResult:
        """派发一个异步子 Agent 任务。"""
        try:
            child_run_id = child_dispatcher(task, agent_name)
            return ToolResult(
                ok=True,
                content=child_run_id,
                metadata={
                    "tool_name": "spawn_child_agent",
                    "child_run_id": child_run_id,
                    "agent_name": agent_name,
                },
            )
        except Exception as e:
            return ToolResult(
                ok=False,
                content=f"Failed to spawn child agent: {e}",
                metadata={"tool_name": "spawn_child_agent", "agent_name": agent_name},
            )

    SCHEMA = {
        "type": "function",
        "function": {
            "name": "spawn_child_agent",
            "description": (
                "把一个独立子任务委派给子 Agent 异步执行。"
                "立即返回 child_run_id 字符串，不等待任务完成。"
                "【单任务模式】派出后立即调用 wait_child_agent(child_run_id) 阻塞等待结果，再回复用户。不要先对用户说'正在等待'就停下。"
                "【并行模式】需要同时派发多个子任务时，先连续调用多次 spawn_child_agent，"
                "然后用 check_child_status 逐一查询各子任务状态：若已 done 则直接从 reply 字段取值；"
                "若仍 running 则对该 child_run_id 单独调用 wait_child_agent 阻塞等待其完成再取结果。"
                "全部子任务结果收齐后，汇总回复用户。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "子 Agent 需要完成的具体任务描述",
                    },
                    "agent_name": {
                        "type": "string",
                        "description": "子 Agent 的角色名称，用于前端展示，如'数据分析师'、'代码审查员'。不填默认为'子Agent'。",
                    },
                },
                "required": ["task"],
                "additionalProperties": False,
            },
        },
    }

    return ToolDefinition(
        name="spawn_child_agent",
        schema=SCHEMA,
        handler=spawn_child_agent,
        risk_level=RiskLevel.SAFE,
    )
