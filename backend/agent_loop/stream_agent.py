"""执行流式智能体循环。"""

from typing import AsyncIterator, Optional, Union

from backend.agent_loop.build_model_request import build_model_request
from backend.agent_loop.build_reply import build_reply
from backend.agent_loop.handle_tool_calls import stream_tool_calls
from backend.agent_loop.types import RunEvent, RunInput
from backend.core.types import (
    ChatMessage,
    StreamChunk,
    ToolCall,
    ToolCallFunction,
)


async def stream_agent(
    *,
    loop,
    run_input: RunInput,
    skip_user_message: bool = False,
    event_index: int = 0,
    run_id: Optional[str] = None,
    workspace_path: Optional[str] = None,
) -> AsyncIterator[Union[RunEvent, str, StreamChunk]]:
    """流式异步运行模式，逐帧产生 Token 或引擎状态事件。"""
    if not skip_user_message:
        last_user = None
        for msg in reversed(loop.state.messages):
            if msg.role == "user":
                last_user = msg
                break
        if not (last_user and last_user.content == run_input.user_input):
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

        raw_reply_chunks: list[str] = []
        tool_call_buffers: dict[int, dict] = {}
        finish_reason: Optional[str] = None

        async for chunk in loop.model_adapter.async_stream_generate(request):
            if chunk.finish_reason:
                finish_reason = chunk.finish_reason
            if chunk.type == "done" and chunk.usage:
                loop.last_usage = chunk.usage
                yield chunk
                continue
            if chunk.type == "thinking_delta":
                yield chunk
                continue
            if chunk.type == "content_delta" and chunk.content_delta:
                yield chunk.content_delta
                raw_reply_chunks.append(chunk.content_delta)
            if chunk.type == "tool_call_delta" and chunk.tool_call_delta:
                for tc in chunk.tool_call_delta.get("tool_calls", [{}]):
                    idx = tc.get("index", 0)
                    if idx not in tool_call_buffers:
                        tool_call_buffers[idx] = {
                            "id": "",
                            "name_chunks": [],
                            "args_chunks": [],
                        }
                    buf = tool_call_buffers[idx]
                    buf["id"] = buf["id"] or tc.get("id", "")
                    fn = tc.get("function", {})
                    buf["name_chunks"].append(fn.get("name", ""))
                    buf["args_chunks"].append(fn.get("arguments", ""))

                    tool_name = "".join(buf["name_chunks"])
                    if tool_name:
                        yield RunEvent(
                            index=event_index + idx,
                            type="assistant_tool_call",
                            tool_name=tool_name,
                            tool_call_id=buf["id"] or f"stream-{idx}",
                            content="".join(buf["args_chunks"]),
                            transient=True,
                        )

        if finish_reason == "tool_calls":
            tool_calls = [
                ToolCall(
                    id=buf["id"],
                    function=ToolCallFunction(
                        name="".join(buf["name_chunks"]),
                        arguments="".join(buf["args_chunks"]),
                    ),
                )
                for buf in tool_call_buffers.values()
            ]
            raw_leadin = "".join(raw_reply_chunks)
            if raw_leadin.strip():
                yield RunEvent(
                    index=event_index,
                    type="assistant_text",
                    content=raw_leadin,
                )
                event_index += 1
            loop.state.messages.append(
                ChatMessage(
                    role="assistant",
                    content=raw_leadin if raw_leadin.strip() else None,
                    tool_calls=tool_calls,
                )
            )

            tool_batch_result = None
            async for item in stream_tool_calls(
                tool_registry=loop.tool_registry,
                tool_calls=tool_calls,
                allow_tool_names=loop.agent_profile.tool_names,
                event_index=event_index,
                session_id=run_input.session_id,
                run_id=run_id,
                workspace_path=workspace_path,
                approval_policy=loop.approval_policy,
                vfs_provider=getattr(loop, "vfs_provider", None),
            ):
                if isinstance(item, RunEvent):
                    yield item
                else:
                    tool_batch_result = item
            for tool_message in tool_batch_result.tool_messages:
                loop.state.messages.append(tool_message)
            if tool_batch_result.paused_for_approval:
                break
            if tool_batch_result.next_event_index is None:
                raise RuntimeError("tool turn missing result")
            event_index = tool_batch_result.next_event_index
            continue
        if finish_reason == "stop":
            raw_reply = "".join(raw_reply_chunks)
            _, final_event, assistant_message = build_reply(
                raw_reply=raw_reply,
                event_index=event_index,
            )
            yield final_event
            loop.state.messages.append(assistant_message)
            break
