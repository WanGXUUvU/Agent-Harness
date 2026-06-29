"""执行工具调用并处理审批分流。"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Optional, Union

from backend.approval.checker import needs_approval
from backend.core.types import ChatMessage, ToolCall
from backend.agent_loop.types import RunEvent, ToolBatchResult
from backend.security.middleware.base import MiddlewarePipeline, ToolCallContext
from backend.security.policy.types import ApprovalPolicy
from backend.security.sandbox import SandboxMiddleware
from backend.tools.registry import ToolRegistry
from backend.tools.result_types import ToolResult

# VFS 取值由编排层注入；引擎层不感知具体 VFS 仓库实现。
# 签名: vfs_provider(run_id) -> vfs 实例或 None
VfsProvider = Callable[[Optional[str]], Any]

_tool_thread_pool = ThreadPoolExecutor(
    max_workers=16,
    thread_name_prefix="tool_worker",
)

TOOL_TIMEOUT = 120


def _resolve_vfs(
    vfs_provider: Optional[VfsProvider],
    run_id: Optional[str],
):
    """通过注入的 provider 取当前 run 的 VFS；无 provider 或无 run_id 时返回 None。"""
    if not vfs_provider or not run_id:
        return None
    return vfs_provider(run_id)


@dataclass
class ToolBatchItem:
    """一轮 assistant tool_calls 里的单个工具调用条目。"""

    tool_call_id: str
    tool_name: str
    arguments: str
    requires_approval: bool
    approval_id: Optional[str] = None
    result_message: Optional[ChatMessage] = None
    result_event: Optional[RunEvent] = None


@dataclass
class ToolBatch:
    """同一轮 assistant 返回的一整批 tool_calls。"""

    run_id: str
    batch_id: str
    items: list[ToolBatchItem] = field(default_factory=list)

    def find_item(self, tool_call_id: str) -> ToolBatchItem:
        for item in self.items:
            if item.tool_call_id == tool_call_id:
                return item
        raise KeyError(f"Tool batch item not found: {tool_call_id}")


def build_tool_batch(
    run_id: str,
    batch_id: str,
    tool_calls: list[ToolCall],
    approval_checker,
) -> ToolBatch:
    items = []
    for tool_call in tool_calls:
        need_approval = approval_checker(tool_call.function.name)
        items.append(
            ToolBatchItem(
                tool_call_id=tool_call.id,
                tool_name=tool_call.function.name,
                arguments=tool_call.function.arguments,
                requires_approval=need_approval,
            )
        )
    return ToolBatch(run_id=run_id, batch_id=batch_id, items=items)


def handle_tool_calls(
    *,
    tool_registry: ToolRegistry,
    tool_calls: list[ToolCall],
    allow_tool_names: Optional[list[str]],
    event_index: int,
    session_id: str = "",
    run_id: Optional[str] = None,
    workspace_path: Optional[str] = None,
    vfs_provider: Optional[VfsProvider] = None,
) -> ToolBatchResult:
    """同步顺序执行一批工具。"""
    events: list[RunEvent] = []
    tool_messages: list[ChatMessage] = []
    current_index = event_index

    for tool_call in tool_calls:
        events.append(
            RunEvent(
                index=current_index,
                type="assistant_tool_call",
                tool_name=tool_call.function.name,
                tool_call_id=tool_call.id,
                content=tool_call.function.arguments,
            )
        )
        current_index += 1

        if (
            allow_tool_names is not None
            and tool_call.function.name not in allow_tool_names
        ):
            raise ValueError(f"Tool not allowed: {tool_call.function.name}")

        context = ToolCallContext(
            tool_name=tool_call.function.name,
            tool_args=tool_call.function.arguments,
            tool_call_id=tool_call.id,
            session_id=session_id,
            run_id=run_id,
            workspace_path=workspace_path,
            allow_tool_names=allow_tool_names,
            vfs=_resolve_vfs(vfs_provider, run_id),
        )

        tool_result = tool_registry.execute_tool_call(
            tool_call.function.name,
            tool_call.function.arguments,
            context,
        )

        if tool_result.ok:
            events.append(
                RunEvent(
                    index=current_index,
                    type="tool_result",
                    tool_name=tool_call.function.name,
                    tool_call_id=tool_call.id,
                    content=tool_result.content,
                    tool_result=tool_result,
                )
            )
            tool_message = ChatMessage(
                role="tool",
                tool_call_id=tool_call.id,
                content=tool_result.content,
            )
        else:
            error_message = (
                tool_result.error.message if tool_result.error else "Tool failed"
            )
            events.append(
                RunEvent(
                    index=current_index,
                    type="tool_error",
                    tool_name=tool_call.function.name,
                    tool_call_id=tool_call.id,
                    content=error_message,
                    tool_result=tool_result,
                )
            )
            tool_message = ChatMessage(
                role="tool",
                tool_call_id=tool_call.id,
                content=f"[TOOL_ERROR] {error_message}",
            )

        current_index += 1
        tool_messages.append(tool_message)

    return ToolBatchResult(
        events=events,
        tool_messages=tool_messages,
        next_event_index=current_index,
    )


async def stream_tool_calls(
    *,
    tool_registry: ToolRegistry,
    tool_calls: list[ToolCall],
    allow_tool_names: Optional[list[str]],
    event_index: int,
    session_id: str,
    run_id: str,
    workspace_path: Optional[str] = None,
    approval_policy: ApprovalPolicy = ApprovalPolicy.NEVER,
    vfs_provider: Optional[VfsProvider] = None,
) -> AsyncIterator[Union[RunEvent, ToolBatchResult]]:
    """异步流式工具执行引擎，支持并发执行与审批拦截。"""
    tool_messages: list[ChatMessage] = []
    current_index = event_index

    def approval_checker(tool_name: str) -> bool:
        risk = tool_registry.get_risk_level(tool_name)
        return needs_approval(approval_policy, risk)

    batch = build_tool_batch(
        run_id=run_id,
        batch_id=f"{run_id}:step:{event_index}",
        tool_calls=tool_calls,
        approval_checker=approval_checker,
    )
    ready_items = []
    pending_items = []

    for item in batch.items:
        if item.requires_approval:
            pending_items.append(item)
        else:
            ready_items.append(item)

    # A. 播报要调用的工具
    for item in batch.items:
        yield RunEvent(
            index=current_index,
            type="assistant_tool_call",
            tool_name=item.tool_name,
            tool_call_id=item.tool_call_id,
            content=item.arguments,
        )
        current_index += 1

    # B. 初始化安全沙箱管道
    pipeline = MiddlewarePipeline([SandboxMiddleware()])

    # C. 并发执行 Worker
    async def run_single_tool(item: ToolBatchItem):
        context = ToolCallContext(
            tool_name=item.tool_name,
            tool_args=item.arguments,
            tool_call_id=item.tool_call_id,
            session_id=session_id,
            run_id=run_id,
            workspace_path=workspace_path,
            allow_tool_names=allow_tool_names,
            vfs=_resolve_vfs(vfs_provider, run_id),
        )

        async def terminal_execute_call() -> ToolResult:
            try:
                loop = asyncio.get_event_loop()
                res = await asyncio.wait_for(
                    loop.run_in_executor(
                        _tool_thread_pool,
                        tool_registry.execute_tool_call,
                        context.tool_name,
                        context.tool_args,
                        context,
                    ),
                    timeout=TOOL_TIMEOUT,
                )
            except asyncio.TimeoutError:
                res = ToolResult.fail(f"Tool timed out after {TOOL_TIMEOUT}s")
            except Exception as e:
                res = ToolResult.fail(str(e))
            return res

        return await pipeline.execute(context, terminal_execute_call)

    tasks = []
    for item in ready_items:
        task = asyncio.create_task(run_single_tool(item))
        tasks.append(task)

    try:
        results = await asyncio.gather(*tasks)
    except Exception as exc:
        for task in tasks:
            if not task.done():
                task.cancel()
        raise exc

    # D. 并发结束，按时序输出最终卡片
    for item, tool_result in zip(ready_items, results):
        if tool_result is None:
            error_message = f"Tool timed out after {TOOL_TIMEOUT}s"
            yield RunEvent(
                index=current_index,
                type="tool_error",
                tool_name=item.tool_name,
                tool_call_id=item.tool_call_id,
                content=error_message,
            )
            tool_message = ChatMessage(
                role="tool",
                tool_call_id=item.tool_call_id,
                content=f"[TOOL_TIMEOUT] {error_message}",
            )
            item.result_message = tool_message
            tool_messages.append(tool_message)
        elif tool_result.ok:
            yield RunEvent(
                index=current_index,
                type="tool_result",
                tool_name=item.tool_name,
                tool_call_id=item.tool_call_id,
                content=tool_result.content,
                tool_result=tool_result,
            )
            tool_message = ChatMessage(
                role="tool",
                tool_call_id=item.tool_call_id,
                content=tool_result.content,
            )
            item.result_message = tool_message
            tool_messages.append(tool_message)
        else:
            error_message = (
                tool_result.error.message
                if tool_result.error and tool_result.error.message
                else "Tool failed"
            )
            yield RunEvent(
                index=current_index,
                type="tool_error",
                tool_name=item.tool_name,
                tool_call_id=item.tool_call_id,
                content=error_message,
                tool_result=tool_result,
            )
            tool_message = ChatMessage(
                role="tool",
                tool_call_id=item.tool_call_id,
                content=f"[TOOL_ERROR] {error_message}",
            )
            item.result_message = tool_message
            tool_messages.append(tool_message)
        current_index += 1

    # E. 处理需要审批的工具
    if pending_items:
        for item in pending_items:
            item.approval_id = item.arguments
            yield RunEvent(
                index=current_index,
                type="approval_required",
                tool_name=item.tool_name,
                tool_call_id=item.tool_call_id,
                content=item.approval_id,
            )
            current_index += 1

        yield ToolBatchResult(
            tool_messages=tool_messages,
            next_event_index=current_index,
            paused_for_approval=True,
        )
        return

    yield ToolBatchResult(
        tool_messages=tool_messages,
        next_event_index=current_index,
    )
