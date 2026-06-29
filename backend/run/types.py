"""
[L8 执行层 - 持久化子模块类型定义]

执行层数据载体：RunSetup + Run I/O 类型。
原先 RunInput/RunOutput/FinalizeRunInput/RunMetadata 在 core/types.py，现归位至本模块。
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from backend.agent.types import AgentDefinition
from backend.core.adapters.chat_completions import ChatCompletionsAdapter
from backend.core.types import ModelUsage
from backend.agent_loop.types import (
    RunEvent,
    RunState,
    RunInput,
    RunOutput,
    RunMetadata,
)
from backend.security.policy.types import ApprovalPolicy

# 公开 API：本模块定义的编排层类型 + 从引擎层 re-export 的 Run I/O 契约。
__all__ = [
    "RunSetup",
    "FinalizeRunInput",
    "RunFinalStatus",
    "RunFinalizationInput",
    # Run I/O 契约（定义在 agent_loop.types，此处 re-export 供编排/API 层统一取用）
    "RunInput",
    "RunOutput",
    "RunMetadata",
    "RunEvent",
    "RunState",
]


@dataclass
class RunSetup:
    """放单次运行预先准备好的稳定依赖。"""

    state: RunState
    # 当前会话采用的原始 agent 定义。
    agent_profile: AgentDefinition
    # 本轮真正发给模型的最终 system prompt。
    runtime_system_prompt: str
    # 已经解析好的模型适配器。
    adapter: ChatCompletionsAdapter
    # 本轮工具调用遵守的审批策略。
    approval_policy: ApprovalPolicy
    # 当前这轮真正生效的 agent 名称。
    effective_agent_name: str
    # 当前工作区物理路径。
    workspace_path: str


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Run I/O
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class FinalizeRunInput(BaseModel):
    """内部用，run 完成时写库。"""

    user_input: str
    reply: str = Field(validation_alias="partial_reply")
    agent_name: Optional[str] = None


class RunFinalStatus(str, Enum):
    """一次 run 的统一终态。"""

    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    FAILED = "failed"


class RunFinalizationInput(BaseModel):
    """放一次 run 结束时的统一收口输入。"""

    # 这次 run 属于哪个 session。
    session_id: str
    # 这次 run 的唯一 ID，也是 VFS / trace / approval 的关联键。
    run_id: str
    # 这次 run 最终以什么状态结束。
    status: RunFinalStatus
    # 当前 run 对应的用户输入；中断/失败场景补 user message 时要用。
    user_input: str
    # 最终完整 reply，或者中断时的 partial reply。
    reply: str
    # 本轮实际执行的 agent 名称；用于 run 摘要和 session 元数据。
    agent_name: Optional[str] = None
    # 本轮正式事件账本。
    events: list[RunEvent] = Field(default_factory=list)
    # 本轮结束时的最新状态快照。
    state: RunState = Field(default_factory=RunState)
    # 模型用量；只有支持用量统计的适配器才会提供。
    usage: Optional[ModelUsage] = None
    # True 表示本次是 resume 续跑，而非新 run。
    is_resume: bool = False
    # True 表示本轮拥有 session 快照写入权；child run 会关掉。
    owns_session: bool = True
