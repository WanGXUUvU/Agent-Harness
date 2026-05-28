"""接口层 DTO 模型 (Data Transfer Objects)。

面向 HTTP API 的请求/响应模型。本模块只承载“HTTP I/O 形状”：
- 请求体（Input）：HTTP 入参的反序列化形状
- 响应体（Output / Summary / Detail / Response）：HTTP 出参的序列化形状
- 错误体（ApiError / ErrorResponse）：统一错误返回的 JSON 结构

核心领域类型（AgentState / AgentEvent / AgentInput / AgentOutput / RunMetadata /
FinalizeRunInput / StreamFrame / SkillSummary / ChatMessage 等）已归位至各自所在
低层模块，本文件只在需要组合它们时按需 import。任何业务层都不应再从此处获取
领域类型——这是九层模型的硬性边界。
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field

# 仅用于本文件 HTTP 响应体的字段组合（如 TraceRunSummary 持有 AgentEvent 列表）。
from agent_prototype.model.types.agent import AgentEvent, AgentState


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 工具调用摘要 — Tool Call Summary
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ToolCallSummary(BaseModel):
    """单次工具调用的详情（持久化读取用）。"""

    id: int
    tool_name: str
    tool_call_id: Optional[str] = None
    status: str
    input_json: Optional[str] = None
    result_json: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None


class RunDetailResponse(BaseModel):
    """GET /sessions/{id}/runs/{run_id} 的响应体。"""

    run_id: str
    session_id: str
    run_status: str
    user_input: str
    reply: str
    agent_name: Optional[str] = None
    skill_name: Optional[str] = None
    created_at: datetime
    tool_calls: list[ToolCallSummary]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Session 管理 — Session
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class CreateSessionInput(BaseModel):
    """/session 创建请求体"""

    session_name: Optional[str] = Field(default=None, min_length=1)
    workspace_path: Optional[str] = None # 绑定的工作区物理绝对路径
    workspace_name: Optional[str] = None # 绑定的工作区文件夹名称
    session_type:Optional[str]=Field(default="coding")

class RenameSessionInput(BaseModel):
    """session 重命名/更新请求体。"""

    session_name: Optional[str] = None  # 新的会话名称（可选）
    permission_profile: Optional[str] = None  # 权限档位（可选）：conservative / standard / full-auto
    model_id: Optional[str] = None
    model_provider_id: Optional[int] = None
    thinking_enabled: Optional[bool] = None
    thinking_effort: Optional[str] = None
    workspace_path: Optional[str] = None # 绑定的工作区物理绝对路径
    workspace_name: Optional[str] = None # 绑定的工作区文件夹名称

class ResetInput(BaseModel):
    """`/reset` 请求体。"""

    session_id: str = Field(min_length=1)

class SessionSummary(BaseModel):
    """session 列表页用的摘要信息。"""

    session_id: str
    session_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_agent_name: Optional[str] = None
    last_skill_name: Optional[str] = None
    message_count: int = 0
    last_reply_preview: Optional[str] = None
    permission_profile: str = "conservative"
    context_tokens: Optional[int] = None
    workspace_path: Optional[str] = None
    workspace_name: Optional[str] = None
    session_type:Optional[str]=Field(default="coding")

class SessionDetail(SessionSummary):
    """session 详情，继承摘要信息并补上完整 state。"""

    state: AgentState
    model_id: Optional[str] = None
    model_provider_id: Optional[int] = None
    thinking_enabled: bool = False
    thinking_effort: str = "medium"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Trace 回放 — Trace
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TraceRunSummary(BaseModel):
    """单次 run 的回放数据。"""

    run_id: str
    session_id: str
    agent_name: Optional[str] = None
    skill_name: Optional[str] = None
    user_input: str
    reply: str
    event_count: int
    created_at: datetime
    finished_at: datetime
    events: list[AgentEvent]

class TraceResponse(BaseModel):
    """`/sessions/{session_id}/trace` 的响应体。"""

    session_id: str
    runs: list[TraceRunSummary]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 上下文压缩 — Compact
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class CompactInput(BaseModel):
    """/compact 请求体"""

    session_id: str = Field(min_length=1)
    trigger_threshold: int = Field(default=12, ge=1)  # 触发 compact 的消息阈值，默认 12，最小 1
    keep_recent_count: int = Field(default=2, ge=1)   # 压缩后保留最近几条原始消息，默认 2，最小 1
    force: bool = Field(default=False)               # 手动触发时置 True，跳过 token 占用率阈值

class CompactOutput(BaseModel):
    """/compact 响应体"""

    state: AgentState
    did_compact: bool
    removed_count: int = 0  # 一共折叠了多少条旧消息
    compact_tokens: Optional[int] = None  # 压缩后实际 input_tokens（来自模型 usage），用于更新 context_tokens

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 统一错误响应 — Error
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ApiError(BaseModel):
    """统一的业务错误内容。"""  # 这个模型只负责描述"错误本身长什么样"

    code: str    # 错误代码，给前端和测试一个稳定的机器可读标识
    message: str  # 错误信息，给用户界面直接展示的可读文本

class ErrorResponse(BaseModel):
    """统一的错误响应体。"""  # 这个模型表示 HTTP 错误返回时，整个 JSON 的外层结构

    error: ApiError  # 把具体错误信息统一收进 error 对象里，避免继续散在顶层

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 设置 — Settings (TASK-072a)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class CreateProviderInput(BaseModel):
    name: str
    base_url: str
    api_key: str

class ProviderOut(BaseModel):
    id: int
    name: str
    base_url: str
    api_key_hint: Optional[str] = None
    is_default: bool
    created_at: datetime

class PatchProviderInput(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    is_default: Optional[bool] = None

class PatchModelInput(BaseModel):
    enabled: Optional[bool] = None
    display_name: Optional[str] = None

class ModelOut(BaseModel):
    id: int
    provider_id: int
    model_id: str
    display_name: str
    enabled: bool
    supports_thinking: bool
    thinking_style: str
    effort_levels: list[str]
    context_length: Optional[int]
    supports_tools: bool

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 工作区管理 — Workspace
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class WorkspaceSummary(BaseModel):
    """已注册工作区的摘要响应体。"""

    id: int
    name: str
    path: str
    created_at: datetime

    class Config:
        from_attributes = True  # 允许从 SQLAlchemy ORM 物理实体直接初始化