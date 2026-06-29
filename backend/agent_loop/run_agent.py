"""执行同步智能体循环。"""

from typing import Optional

from backend.agent_loop.build_model_request import build_model_request
from backend.agent_loop.build_reply import build_reply
from backend.agent_loop.handle_tool_calls import handle_tool_calls
from backend.agent_loop.types import RunEvent, RunInput, RunMetadata, RunOutput
from backend.core.types import ChatMessage


def run_agent(
    *,
    loop,
    run_input: RunInput,
    run_id: Optional[str] = None,
) -> RunOutput:
    """同步运行模式：一次性执行到底。"""
    events: list[RunEvent] = []
    event_index = 0

    loop.state.messages.append(
        ChatMessage(role="user", content=run_input.user_input)
    )
    loop.state.step += 1

    while True:
        request = build_model_request(
            agent_profile=loop.agent_profile,
            runtime_system_prompt=loop.runtime_system_prompt,
            state=loop.state,
            tool_registry=loop.tool_registry,
        )
        response = loop.model_adapter.generate(request)
        assistant_message = response.assistant_message
        tool_calls = assistant_message.tool_calls or []

        if tool_calls:
            leadin = assistant_message.content or ""
            if leadin.strip():
                events.append(
                    RunEvent(
                        index=event_index,
                        type="assistant_text",
                        content=leadin,
                    )
                )
                event_index += 1
            loop.state.messages.append(assistant_message)
            tool_batch = handle_tool_calls(
                tool_registry=loop.tool_registry,
                tool_calls=tool_calls,
                allow_tool_names=loop.agent_profile.tool_names,
                event_index=event_index,
                session_id=run_input.session_id,
                run_id=run_id,
                workspace_path=getattr(run_input, "workspace_path", None),
                vfs_provider=getattr(loop, "vfs_provider", None),
            )
            events.extend(tool_batch.events)
            event_index = tool_batch.next_event_index
            for tool_message in tool_batch.tool_messages:
                loop.state.messages.append(tool_message)
            continue

        raw_reply = response.content or ""
        reply, final_event, assistant_message = build_reply(
            raw_reply=raw_reply,
            event_index=event_index,
        )
        events.append(final_event)
        loop.state.messages.append(assistant_message)

        return RunOutput(
            reply=reply,
            state=loop.state,
            events=events,
            usage=response.usage,
            metadata=RunMetadata(session_id=run_input.session_id),
        )
