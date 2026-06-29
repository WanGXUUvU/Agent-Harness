"""处理历史消息压缩。"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.agent_loop.types import RunState
from backend.core.types import (
    ChatMessage,
    ModelAdapter,
    ModelConfig,
    ModelRequest,
)
from backend.infra.db.orm_models import ModelSetting, SessionRecord
from backend.memory.run.store import RunTraceStore
from backend.session.store import SessionStore

logger = logging.getLogger(__name__)

COMPACT_SUMMARY_PREFIX = (
    "[COMPACT_SUMMARY]\n"
    "这是一份结构化上下文摘要，用于替代压缩前的完整对话历史。"
    "后续模型应把它视为继续执行任务的权威上下文。"
    "除非摘要中明确标注为逐字引用，否则它不是原始对话逐字记录。"
)

NO_TOOLS_PREAMBLE = """你现在处于上下文压缩模式。
你没有任何工具可用。
不要尝试调用读取文件、执行命令、搜索、访问外部系统等任何工具。
如果你认为需要额外信息，请只基于当前对话中已经出现的信息完成压缩。
只按下面要求输出压缩结果，不要输出额外说明。"""

BASE_COMPACT_PROMPT = """你的任务是为当前对话生成一份结构化、足够详细的上下文摘要。
这份摘要会替代压缩前的完整对话历史，用来节省上下文空间，
同时必须保留后续继续执行任务所需的全部关键信息。

你必须包含下面 9 个部分。请把分析过程写在 <analysis> 标签内，
把最终摘要写在 <summary> 标签内。

<analysis>
请逐步分析：
1. 用户最初的目标是什么，后续又补充或修正了哪些要求？
2. 对话中出现了哪些重要对象、文件、接口、数据、代码片段、错误或处理结果？
3. 哪些事项已经完成，哪些事项仍未完成？
4. 压缩发生前，当前任务正处于什么准确状态？
</analysis>

<summary>
1. PRIMARY REQUEST AND INTENT:
   （说明用户的原始目标，以及后续对目标的补充、收窄或修正。要具体。）

2. KEY TECHNICAL CONCEPTS:
   （列出对继续任务有用的关键概念、术语、架构决策、业务规则、工具能力或约束。）

3. FILES AND CODE SECTIONS:
   （如果对话涉及文件、代码、接口、数据结构或配置，请列出路径/名称和关键内容。
    如有必要，包含精确代码片段或行号；如果不涉及代码，也要说明相关对象或数据。）

4. ERRORS AND FIXES:
   （列出遇到的错误、误解、失败尝试、根因和最终处理方式。）

5. PROBLEM SOLVING:
   （说明已经解决的问题、采用 of 推理或权衡，以及仍在调查或需要继续判断的点。）

6. ALL USER MESSAGES:
   （逐字引用用户发送过的每一条消息。不要改写，不要概括。）

7. PENDING TASKS:
   （列出用户明确要求但尚未完成的事项。）

8. CURRENT WORK STATE:
   （准确描述压缩发生前的当前状态，例如：刚完成某项修改、正在等待验证、
    正准备继续某个步骤、或已经没有未完成工作。）

9. OPTIONAL NEXT STEP SUGGESTION:
   （基于当前对话给出一个具体下一步建议。
    必须引用用户或助手的原文来说明为什么建议这一步。）
</summary>"""


class CompactInput(BaseModel):
    """压缩请求参数。"""

    session_id: str = Field(min_length=1)
    trigger_threshold: int = Field(default=12, ge=1)
    force: bool = Field(default=False)


class CompactOutput(BaseModel):
    """压缩结果。"""

    state: RunState
    did_compact: bool
    removed_count: int = 0
    compact_tokens: Optional[int] = None


@dataclass
class CompactedMessagesResult:
    """压缩后的消息结果。"""

    messages: list[ChatMessage]
    compact_tokens: Optional[int] = None


def extract_compact_summary(raw_output: str) -> str:
    """从模型输出里取出 <summary> 内容。

    如果模型没有按标签输出，就尽量去掉 analysis 段后返回剩余内容，避免压缩失败。
    """
    text = (raw_output or "").strip()
    summary_match = re.search(r"<summary>([\s\S]*?)</summary>", text, re.IGNORECASE)
    if summary_match:
        return summary_match.group(1).strip()
    return re.sub(
        r"<analysis>[\s\S]*?</analysis>", "", text, flags=re.IGNORECASE
    ).strip()


def build_compact_summary_message(summary_text: str) -> ChatMessage:
    """把摘要文本包装成一条 system 消息。"""
    return ChatMessage(
        role="system",
        content=f"{COMPACT_SUMMARY_PREFIX}\n\n{summary_text.strip()}",
    )


class HistoryCompactor:
    """协调模型适配器，把完整历史消息压缩成新的消息列表。"""

    def __init__(self, adapter: ModelAdapter):
        self.adapter = adapter

    def compact_messages(self, messages: list[ChatMessage]) -> CompactedMessagesResult:
        """把原始消息列表压缩成一条 compact summary system message。"""
        if not messages:
            return CompactedMessagesResult(messages=[])

        system_prompt = f"{NO_TOOLS_PREAMBLE}\n\n{BASE_COMPACT_PROMPT}"

        user_content_lines = [
            "下面是需要压缩的完整对话历史：",
            "<conversation>",
        ]
        for m in messages:
            user_content_lines.append(f"[{m.role}]: {m.content or ''}")
        user_content_lines.append("</conversation>")
        user_content_lines.append("\n请只返回分析和摘要（使用 <analysis> 和 <summary> 标签包裹），不要输出额外说明。")
        user_content = "\n".join(user_content_lines)

        request = ModelRequest(
            messages=[
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_content),
            ],
            tools=[],
            config=ModelConfig(stream=False),
        )
        summary_response = self.adapter.generate(request=request)
        summary_text = extract_compact_summary(
            raw_output=summary_response.content or "",
        )

        if summary_response.usage and summary_response.usage.input_tokens:
            compact_tokens = summary_response.usage.input_tokens
        else:
            compact_tokens = None

        if not summary_text:
            return CompactedMessagesResult(messages=[], compact_tokens=compact_tokens)

        return CompactedMessagesResult(
            messages=[build_compact_summary_message(summary_text=summary_text)],
            compact_tokens=compact_tokens,
        )


class CompactService:
    """管理对话历史压缩生命周期。"""

    def __init__(self, db: Session):
        """使用当前数据库会话装配压缩服务。"""
        self.db = db
        self.store = SessionStore(db)
        self._run_store = RunTraceStore(db)

    def auto_compact_in_memory(
        self,
        state: RunState,
        context_tokens: int,
        context_length: int,
        compactor: HistoryCompactor,
        force: bool = False,
    ) -> CompactOutput:
        """在内存中评估并执行一次压缩，不做持久化。"""
        if not state.messages:
            return CompactOutput(state=state, did_compact=False, removed_count=0)

        if not force:
            if context_tokens == 0 or context_length == 0:
                return CompactOutput(state=state, did_compact=False, removed_count=0)
            if context_tokens / context_length < 0.7:
                return CompactOutput(state=state, did_compact=False, removed_count=0)

        compacted = compactor.compact_messages(state.messages)

        if not compacted.messages:
            raise ValueError("Compact summary is empty")

        compacted_state = state.model_copy(update={"messages": compacted.messages})
        return CompactOutput(
            state=compacted_state,
            did_compact=True,
            removed_count=max(len(state.messages) - len(compacted.messages), 0),
            compact_tokens=compacted.compact_tokens,
        )

    def compact_session(self, payload: CompactInput) -> CompactOutput:
        """对指定会话执行压缩，并将结果持久化。"""
        state = self.store.get(session_id=payload.session_id)
        if state is None:
            raise ValueError("Session not found")

        record = (
            self.db.query(SessionRecord)
            .filter(SessionRecord.session_id == payload.session_id)
            .first()
        )
        context_tokens = record.context_tokens or 0 if record else 0

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
        context_length = model_setting.context_length or 0 if model_setting else 0

        # 无 token 信息时退回消息数量阈值判断
        force_by_count = (context_tokens == 0 or context_length == 0) and len(
            state.messages
        ) >= payload.trigger_threshold

        from backend.run.setup import build_model_adapter

        adapter = build_model_adapter(
            db=self.db,
            session_id=payload.session_id,
        )
        compactor = HistoryCompactor(adapter=adapter)

        compact_result = self.auto_compact_in_memory(
            state=state,
            context_tokens=context_tokens,
            context_length=context_length,
            force=payload.force or force_by_count,
            compactor=compactor,
        )

        if not compact_result.did_compact:
            return compact_result

        record = self.store.load_record(session_id=payload.session_id)
        try:
            if compact_result.compact_tokens is not None:
                new_context_tokens = compact_result.compact_tokens
            else:
                new_context_tokens = (
                    sum(len(m.content or "") for m in compact_result.state.messages)
                    // 4
                )

            self.store.save_state(
                session_id=payload.session_id,
                state=compact_result.state,
                session_name=record.session_name if record else payload.session_id,
                last_agent_name=record.last_agent_name if record else None,
                last_reply_preview=record.last_reply_preview if record else None,
                context_tokens=new_context_tokens,
            )
            runs = self._run_store.list_run_records(session_id=payload.session_id)
            parent_runs = [r for r in runs if r.parent_run_id is None]
            for run in parent_runs:
                run.is_active = "0"

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return compact_result
