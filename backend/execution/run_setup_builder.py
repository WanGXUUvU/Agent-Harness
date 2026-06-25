"""run setup 构建器。

职责：
- 读取 session 主记录和状态快照。
- 构建模型适配器并解析审批策略。
- 选择运行时 agent definition。
- 在进入 run 前评估并执行自动压缩。

上游：
- RunService
- ResumeRunService

下游：
- SessionStore
- AgentDefinitionService
- ContextAssembler
- CompactService

不负责：
- 不驱动 AgentRunner 执行。
- 不落库。
- 不查询 trace。
"""

from typing import Optional

from sqlalchemy.orm import Session

from backend.agent.types import AgentDefinition
from backend.agent.definition import AgentDefinitionService
from backend.context.assembler import ContextAssembler
from backend.context.compaction import HistoryCompactor
from backend.core.adapters.chat_completions import ChatCompletionsAdapter
from backend.execution.persistence.types import RunInput, RunSetup
from backend.execution.runtime.types import RunState
from backend.infra.db.orm_models import (
    ModelSetting,
    ProviderConfig,
    SessionRecord,
)
from backend.memory.session.store import SessionStore
from backend.memory.summary.service import CompactService
from backend.prompt.builder import build_runtime_system_prompt
from backend.prompt.strategies.thinking import build_thinking_payload
from backend.security.policy.types import PROFILES


class RunSetupBuilder:
    """负责为一次运行构建稳定的 run setup。"""

    def __init__(self, db: Session):
        self.db = db
        self.store = SessionStore(db)

    def build(self, run_input: RunInput) -> RunSetup:
        """按主链顺序构建一次运行所需的稳定 setup。"""
        session_id = run_input.session_id
        session_record = self._load_session_record(session_id)
        session_state = self._load_session_state(session_id)
        model_adapter = self._build_model_adapter(session_id, session_record)
        session_state = self._maybe_auto_compact_state(
            state=session_state,
            record=session_record,
            adapter=model_adapter,
        )
        effective_agent_name = self._resolve_agent_name(run_input)
        agent_definition = self._load_agent_definition(effective_agent_name)
        runtime_system_prompt = self._build_runtime_system_prompt(
            run_input=run_input,
            workspace_path=(
                session_record.workspace_path if session_record else None
            ),
            definition=agent_definition,
        )
        approval_policy = self._resolve_approval_policy(session_record)

        return RunSetup(
            state=session_state,
            agent_profile=agent_definition.model_copy(
                update={"system_prompt": runtime_system_prompt}
            ),
            adapter=model_adapter,
            approval_policy=approval_policy,
            effective_agent_name=effective_agent_name,
            workspace_path=(
                session_record.workspace_path if session_record else ""
            ),
        )

    def build_model_adapter(self, session_id: str) -> ChatCompletionsAdapter:
        """为恢复运行等场景单独构建模型适配器。"""
        return self._build_model_adapter(session_id)

    def resolve_approval_policy(self, record: Optional[SessionRecord]):
        """对外暴露审批策略解析，供恢复运行等链路复用。"""
        return self._resolve_approval_policy(record)

    def _build_runtime_system_prompt(
        self,
        *,
        run_input: RunInput,
        workspace_path: Optional[str],
        definition: AgentDefinition,
    ) -> str:
        """构建本轮真正传给模型的 runtime system prompt。"""
        prompt_context_builder = ContextAssembler(
            self.db,
            build_runtime_system_prompt=build_runtime_system_prompt,
        )
        prompt_context = prompt_context_builder.assemble(
            run_input=run_input,
            workspace_path=workspace_path,
            definition=definition,
        )
        return prompt_context.system_prompt

    def _load_session_record(
        self, session_id: str
    ) -> Optional[SessionRecord]:
        """读取 session 主记录。"""
        return (
            self.db.query(SessionRecord)
            .filter(SessionRecord.session_id == session_id)
            .first()
        )

    def _load_session_state(self, session_id: str) -> RunState:
        """读取 session 最新状态快照。"""
        return self.store.get(session_id) or RunState()

    def _resolve_context_length(
        self,
        record: Optional[SessionRecord],
        fallback_tokens: int,
    ) -> int:
        """解析本次运行的上下文长度。"""
        model_setting = (
            self.db.query(ModelSetting)
            .filter(
                ModelSetting.model_id == record.model_id,
                ModelSetting.provider_id == record.model_provider_id,
            )
            .first()
            if record and record.model_id and record.model_provider_id
            else None
        )
        if model_setting and model_setting.context_length:
            return model_setting.context_length
        return fallback_tokens

    def _resolve_agent_name(
        self,
        run_input: RunInput,
    ) -> str:
        """解析本轮实际使用的 agent 名称。"""
        return run_input.agent_name or "default"

    def _load_agent_definition(self, agent_name: str) -> AgentDefinition:
        """加载本轮实际采用的 agent 定义。"""
        return AgentDefinitionService(self.db).load_definition(agent_name)

    def _resolve_approval_policy(self, record: Optional[SessionRecord]):
        """根据 session 权限档位选择审批策略。"""
        profile_name = (
            record.permission_profile
            if record and record.permission_profile
            else "conservative"
        )
        return PROFILES.get(profile_name, PROFILES["conservative"]).approval_policy

    def _maybe_auto_compact_state(
        self,
        *,
        state: RunState,
        record: Optional[SessionRecord],
        adapter: ChatCompletionsAdapter,
    ) -> RunState:
        """在进入 run 前按当前上下文预算执行一次自动压缩。"""
        if not state.messages:
            return state

        context_tokens = (
            record.context_tokens if record and record.context_tokens else 0
        )
        context_length = self._resolve_context_length(record, context_tokens)
        compactor = HistoryCompactor(adapter)
        compact_result = CompactService(self.db).auto_compact_in_memory(
            state=state,
            context_tokens=context_tokens,
            context_length=context_length,
            compactor=compactor,
        )
        return compact_result.state

    def _build_model_adapter(
        self,
        session_id: str,
        record: Optional[SessionRecord] = None,
    ) -> ChatCompletionsAdapter:
        """根据 session 绑定的 provider/model 配置构建模型适配器。"""
        if record is None:
            record = self._load_session_record(session_id)

        if (
            record is None
            or record.model_provider_id is None
            or record.model_id is None
        ):
            raise ValueError(
                "当前会话未配置模型，请在设置中选择 Provider 和模型后再开始对话"
            )

        provider = (
            self.db.query(ProviderConfig)
            .filter(ProviderConfig.id == record.model_provider_id)
            .first()
        )
        if provider is None:
            raise ValueError("会话关联的 Provider 已被删除，请重新选择模型")

        model_setting = (
            self.db.query(ModelSetting)
            .filter(
                ModelSetting.model_id == record.model_id,
                ModelSetting.provider_id == record.model_provider_id,
            )
            .first()
        )
        thinking_payload = build_thinking_payload(
            style=model_setting.thinking_style if model_setting else "none",
            enabled=bool(record.thinking_enabled),
            effort=record.thinking_effort or "medium",
        )
        return ChatCompletionsAdapter(
            api_key=provider.api_key,
            base_url=provider.base_url,
            model=record.model_id,
            extra_payload=thinking_payload,
        )
