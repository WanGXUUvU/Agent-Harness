"""
[九层模型 - L1 领域类型层 (Model Domain Layer)]

Agent 运行时核心领域类型。

本模块承载所有 agent 运行时（session 状态、事件、run 请求/响应等）的语义
类型定义。它们原先错误地寄生在 api/dto/schemas.py 中，导致 L5/L6/L8/L9
层全部向上依赖 API 层。归位到 L1 后所有上层只需 import 低层即可使用。

仅依赖：标准库 + pydantic + model.types.domain（同层）。
"""

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

from agent_prototype.model.types.domain import ChatMessage, ToolResult


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 运行时消息 & 状态 — Runtime Message & State
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AgentState(BaseModel):
    """某个 session 的最新状态快照。"""

    messages: list[ChatMessage] = Field(default_factory=list)
    step: int = 0
    agent_name: Optional[str] = None


class AgentEvent(BaseModel):
    """一次 run 中的结构化事件。"""

    index: int
    type: Literal[
        "assistant_tool_call",
        "tool_result",
        "tool_error",
        "final_answer",
        "approval_required",
        "approval_result",
        "thinking",
    ]
    content: Optional[str] = None
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_result: Optional[ToolResult] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Run 请求 & 响应 — Run I/O
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AgentInput(BaseModel):
    """`/run` 请求体。"""

    agent_name: Optional[str] = None
    session_id: str = Field(min_length=1)
    user_input: str = Field(min_length=1)
    skill_name: Optional[str] = None


class RunMetadata(BaseModel):
    """一次 /run 的轻量元信息。"""

    session_id: str
    run_id: str = ""
    agent_name: Optional[str] = None
    skill_name: Optional[str] = None


class AgentOutput(BaseModel):
    """`/run` 响应体。"""

    reply: str
    state: AgentState
    events: list[AgentEvent]
    metadata: RunMetadata
    usage: Optional[Any] = None


class FinalizeRunInput(BaseModel):
    """内部用，run 完成时写库。"""

    user_input: str
    partial_reply: str
    agent_name: Optional[str] = None
    skill_name: Optional[str] = None
