"""定义数据库 ORM 模型。"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from .engine import Base

# ── Session 相关表 ────────────────────────────────────────────────────────────


class SessionRecord(Base):
    """保存会话快照和列表摘要字段。"""

    __tablename__ = "session_records"

    session_id = Column(String, primary_key=True, index=True)
    session_name = Column(String, nullable=True)
    state_json = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    last_agent_name = Column(String, nullable=True, index=True)
    message_count = Column(Integer, nullable=False, default=0, server_default="0")
    last_reply_preview = Column(String(120), nullable=True)
    permission_profile = Column(String, nullable=False, default="conservative")
    context_tokens = Column(Integer, nullable=True)
    # 模型选择（NULL 表示使用环境变量 RUN_MODEL）
    model_provider_id = Column(
        Integer, ForeignKey("provider_configs.id", ondelete="SET NULL"), nullable=True
    )
    model_id = Column(String, nullable=True)
    thinking_enabled = Column(Integer, nullable=False, default=0)  # 0/1
    thinking_effort = Column(String, nullable=False, default="medium")
    workspace_path = Column(String, nullable=True)
    workspace_name = Column(String, nullable=True)
    parent_session_id = Column(
        String,
        ForeignKey("session_records.session_id", ondelete="SET NULL"),
        nullable=True,
    )
    fork_message_index = Column(Integer, nullable=True)


class SessionRunRecord(Base):
    """保存单次运行的摘要信息。"""

    __tablename__ = "session_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String,
        ForeignKey("session_records.session_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    parent_run_id = Column(
        String,
        ForeignKey("session_runs.run_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    run_id = Column(String, unique=True, nullable=False)
    run_status = Column(String, nullable=False, default="running")
    agent_name = Column(String, nullable=True, index=True)
    user_input = Column(Text, nullable=False)
    reply = Column(Text, nullable=False)
    event_count = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    finished_at = Column(DateTime, server_default=func.now(), nullable=False)
    is_active = Column(String, nullable=False, default=1, server_default="1")

    events = relationship(
        "SessionRunEventRecord",
        cascade="all,delete-orphan",
        order_by="SessionRunEventRecord.event_index",
    )


class ToolCallRecord(Base):
    """保存单次工具调用记录。"""

    __tablename__ = "tool_call_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(
        String,
        ForeignKey("session_runs.run_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    tool_name = Column(String, nullable=False)
    tool_call_id = Column(String, nullable=True)  # LLM 分配的 ID
    status = Column(
        String, nullable=False, default="running"
    )  # running / completed / failed / timeout / cancelled
    input_json = Column(Text, nullable=True)  # 工具入参
    result_json = Column(Text, nullable=True)  # 工具结果
    started_at = Column(DateTime, server_default=func.now(), nullable=False)
    finished_at = Column(DateTime, nullable=True)  # 执行完才有


class SessionRunEventRecord(Base):
    """保存单次运行的逐条事件。"""

    __tablename__ = "session_run_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(
        String,
        ForeignKey("session_runs.run_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    event_index = Column(Integer, nullable=False)
    type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    tool_name = Column(String, nullable=True)
    tool_call_id = Column(String, nullable=True)
    tool_result_json = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


# ── Agent 定义表 ──────────────────────────────────────────────────────────────


class AgentDefinitionRecord(Base):
    """保存 Agent 定义。"""

    __tablename__ = "agent_definitions"

    agent_id = Column(String, primary_key=True, index=True)
    definition_json = Column(Text, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ── 审批表 ────────────────────────────────────────────────────────────────────


class PendingApproval(Base):
    """保存待审批的工具调用。"""

    __tablename__ = "pending_approvals"

    id = Column(String, primary_key=True)  # UUID，审批单号
    session_id = Column(String, nullable=False, index=True)  # 关联 session
    run_id = Column(String, nullable=False)  # 关联 run
    batch_id = Column(String, nullable=True, index=True)  # 关联同一批 tool_calls
    tool_name = Column(String, nullable=False)  # 要执行的工具
    tool_call_id = Column(String, nullable=True)
    arguments = Column(Text, nullable=False)  # 工具参数 JSON
    status = Column(
        String, nullable=False, default="pending"
    )  # pending / approved / rejected
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    saved_messages = Column(JSON, nullable=False)
    event_index = Column(Integer, nullable=False)


# ── Provider & 模型配置表 ─────────────────────────────────────────────────────


class ProviderConfig(Base):
    """保存模型服务商配置。"""

    __tablename__ = "provider_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    base_url = Column(String, nullable=False)
    api_key = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    is_default = Column(Integer, nullable=False, default=0, server_default="0")

    models = relationship("ModelSetting", cascade="all,delete-orphan")


class ModelSetting(Base):
    """保存服务商下的模型配置。"""

    __tablename__ = "model_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_id = Column(
        Integer,
        ForeignKey("provider_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_id = Column(String, nullable=False)  # 如 "deepseek-v4-flash"
    display_name = Column(String, nullable=True)  # 覆盖显示名
    enabled = Column(Integer, nullable=False, default=0)  # 0/1，是否出现在对话框
    supports_thinking = Column(Integer, nullable=False, default=0)
    thinking_style = Column(
        String, nullable=True
    )  # "deepseek_style" | "sensenova_style" | "none"
    effort_levels = Column(Text, nullable=True)  # JSON 字符串，如 '["low","high"]'
    context_length = Column(Integer, nullable=True)
    supports_tools = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # 同一个 Provider 下，同一个 model_id 不能重复
    __table_args__ = (UniqueConstraint("provider_id", "model_id"),)


# ── 工作区表 ──────────────────────────────────────────────────────────────────


class WorkspaceRecord(Base):
    """保存已登记的工作区路径。"""

    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)  # 文件夹显示名称
    path = Column(String, nullable=False, unique=True, index=True)  # 物理绝对路径
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
