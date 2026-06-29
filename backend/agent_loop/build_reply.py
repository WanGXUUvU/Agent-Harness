"""把模型原始回复转成最终输出对象。"""

from backend.agent_loop.types import RunEvent
from backend.core.types import ChatMessage


def build_reply(raw_reply: str, event_index: int) -> tuple[str, RunEvent, ChatMessage]:
    """把原始模型文本转成 reply、final event 和 assistant message。"""
    reply = (raw_reply or "").strip()
    event = RunEvent(
        index=event_index,
        type="final_answer",
        content=reply,
    )
    assistant_message = ChatMessage(role="assistant", content=raw_reply)
    return reply, event, assistant_message
