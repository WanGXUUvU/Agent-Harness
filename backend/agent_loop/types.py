"""定义运行时状态、事件和输入输出类型。"""

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

from backend.core.types import ChatMessage
from backend.tools.result_types import ToolResult


class RunState(BaseModel):
    """某个会话的最新状态快照。"""

    messages: list[ChatMessage] = Field(default_factory=list)
    step: int = 0
    agent_name: Optional[str] = None


class RunEvent(BaseModel):
    """一次运行中的结构化事件。"""

    index: int
    type: Literal[
        "assistant_text",
        "assistant_tool_call",
        "tool_result",
        "tool_error",
        "final_answer",
        "approval_required",
        "thinking",
    ]
    content: Optional[str] = None
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_result: Optional[ToolResult] = None
    transient: bool = False


class ToolBatchResult(BaseModel):
    """一次工具批次执行结束后的统一账单。"""

    events: list[RunEvent] = Field(default_factory=list)
    tool_messages: list[ChatMessage] = Field(default_factory=list)
    next_event_index: int
    paused_for_approval: bool = False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Run I/O 契约
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 以下三个类型是引擎对外的输入输出契约，由编排层 (run) 与 API 层共享。
# 放在引擎层是为了保证 agent_loop 不反向依赖 run —— run.types 仅 re-export。


class RunInput(BaseModel):
    """运行接口请求体。"""

    # 用户显式指定的 agent；为空时交给 run_setup 决定默认值。
    agent_name: Optional[str] = None
    # 本轮 run 归属的 session。
    session_id: str = Field(min_length=1)
    # 用户本轮输入的原始文本。
    user_input: str = Field(min_length=1)
    # 可选的 skill 名称，仅作为元信息向下游透传。
    skill_name: Optional[str] = None
    # 前端显式传入的工作区路径；当前主链仍以 session 绑定的 workspace 为准。
    workspace_path: Optional[str] = None


class RunMetadata(BaseModel):
    """一次运行的轻量元信息。"""

    session_id: str
    run_id: str = ""
    agent_name: Optional[str] = None


class RunOutput(BaseModel):
    """运行接口响应体。"""

    reply: str
    state: RunState
    events: list
    metadata: RunMetadata
    usage: Optional[Any] = None
