"""应用服务层 (Application Layer) - 工具调用引擎

职责：
1. 驱动大模型解析出的工具（ToolCall）顺序或并发执行。
2. 串联工具执行拦截器管道（ToolInterceptorPipeline），依次执行安全、审批等洋葱圈中间件。

不负责：
1. 物理工具底层逻辑的具体实现。
2. 审批数据的持久化数据库读写。

数据流向：
- 输入：ToolCall 列表入参及执行上下文。
- 输出：包含所有工具返回消息与事件的 ToolTurnResult。
- 上游来源：agent_prototype/execution/runtime/agent_runtime.py。
- 下游流向：传递到拦截器中间件管道，并最终分发至 agent_prototype/tools/* 底层方法。
"""

# ── 标准库 ────────────────────────────────────────────────────────────────────
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncIterator, Optional, Union

# ── 本地模块 ──────────────────────────────────────────────────────────────────
from agent_prototype.core.types import ChatMessage, ToolCall
from agent_prototype.execution.runtime.types import AgentEvent
from agent_prototype.security.policy.types import ApprovalPolicy
from agent_prototype.tools.registry import ToolRegistry
from agent_prototype.tools.result_types import ToolResult
from agent_prototype.security.middleware.base import MiddlewarePipeline, ToolCallContext
from agent_prototype.security.sandbox.middleware import SandboxMiddleware
from agent_prototype.security.approval.middleware import (
    ApprovalMiddleware,
    ApprovalRequiredException,
)

# ── 线程池 ────────────────────────────────────────────────────────────────────

# 模块级单例，整个进程共用，超时泄漏的线程也被限在 16 个以内
_tool_thread_pool = ThreadPoolExecutor(
    max_workers=16,
    thread_name_prefix="tool_worker",
)

TOOL_TIMEOUT = 120  # 单次工具调用最长等待秒数


# ── 数据类 ────────────────────────────────────────────────────────────────────

from agent_prototype.execution.runtime.types import ToolTurnResult

# ── 同步工具执行 ──────────────────────────────────────────────────────────────


def handle_tool_calls(
    tool_registry: ToolRegistry,
    tool_calls: list[ToolCall],
    allow_tool_names: Optional[list[str]],
    event_index: int,
) -> ToolTurnResult:
    """同步工具执行器：老老实实、挨个同步去调用大模型想用的那批工具。
    在调用前会进行白名单安全拦截（如果工具不被允许，直接报错）。全部调完后把产生的事件和工具答复包装成结算账单。

    需要拿到的东西：
    - tool_registry: 工具箱仓库（工具注册中心）。
    - tool_calls: 大模型发出的工具调用请求列表。
    - allow_tool_names: 这次允许执行的工具白名单列表（可选）。
    - event_index: 序列号起始索引。

    会给出来的结果：
    - 一个结算账单 ToolTurnResult 对象。
    """
    events: list[AgentEvent] = []
    tool_messages: list[ChatMessage] = []
    current_index = event_index

    for tool_call in tool_calls:
        events.append(
            AgentEvent(
                index=current_index,
                type="assistant_tool_call",
                tool_name=tool_call.function.name,
                tool_call_id=tool_call.id,
                content=tool_call.function.arguments,
            )
        )
        current_index += 1

        if allow_tool_names is not None and tool_call.function.name not in allow_tool_names:
            raise ValueError(f"Tool not allowed: {tool_call.function.name}")

        tool_result = tool_registry.execute_tool_call(
            tool_call.function.name,
            tool_call.function.arguments,
        )

        if tool_result.ok:
            events.append(
                AgentEvent(
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
            error_message = tool_result.error.message if tool_result.error else "Tool failed"
            events.append(
                AgentEvent(
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

    return ToolTurnResult(
        events=events,
        tool_messages=tool_messages,
        next_event_index=current_index,
    )


# ── 异步工具执行（含审批与并发） ───────────────────────────────────────────────


async def async_handle_tool_calls(
    tool_registry: ToolRegistry,
    tool_calls: list[ToolCall],
    allow_tool_names: Optional[list[str]],
    event_index: int,
    session_id: str,
    run_id: str,
    workspace_path: Optional[str] = None,
    on_tool_start=None,
    on_tool_finish=None,
    approval_policy: ApprovalPolicy = ApprovalPolicy.NEVER,
    on_approval_required=None,
    saved_messages: Optional[list[ChatMessage]] = None,
    session_type: str = "coding",
) -> AsyncIterator[Union[AgentEvent, ToolTurnResult]]:
    """异步流式工具执行引擎。
    
    支持多工具基于 asyncio.gather 并发调度、中间件链执行拦截、
    跨线程多生产者流式进度实时汇聚（asyncio.Queue）以及阻断性异常（如审批）时的并发安全生命周期回收。
    """
    tool_messages: list[ChatMessage] = []
    current_index = event_index

    # 1. 根据会话模式初始化安全中间件管道
    if session_type == "coding":
        pipeline = MiddlewarePipeline([SandboxMiddleware(), ApprovalMiddleware()])
    else:
        pipeline = MiddlewarePipeline([ApprovalMiddleware()])

    # 2. 播报工具启动通知事件
    for tool_call in tool_calls:
        yield AgentEvent(
            index=current_index,
            type="assistant_tool_call",
            tool_name=tool_call.function.name,
            tool_call_id=tool_call.id,
            content=tool_call.function.arguments,
        )
        current_index += 1

    # 3. 创建多生产者共享队列，汇聚后台工作线程的实时进度
    event_queue = asyncio.Queue()

    async def make_progress_callback(tc_id: str, t_name: str):
        async def on_progress(text: str) -> None:
            await event_queue.put(
                AgentEvent(
                    index=0,
                    type="tool_progress",
                    tool_name=t_name,
                    tool_call_id=tc_id,
                    content=text,
                )
            )
        return on_progress

    # 4. 定义单个工具的执行协程 Worker
    async def run_single_tool(tc: ToolCall, idx_slot: list[int]):
        if allow_tool_names is not None and tc.function.name not in allow_tool_names:
            raise ValueError(f"Tool not allowed: {tc.function.name}")

        risk = tool_registry.get_risk_level(tc.function.name)
        progress_cb = await make_progress_callback(tc.id, tc.function.name)

        context = ToolCallContext(
            tool_name=tc.function.name,
            tool_args=tc.function.arguments,
            tool_call_id=tc.id,
            session_id=session_id,
            run_id=run_id,
            extra={
                "workspace_path": workspace_path,
                "allow_tool_names": allow_tool_names,
                "risk_level": risk,
                "on_approval_required": on_approval_required,
                "saved_messages": saved_messages,
                "current_index": idx_slot[0],
                "approval_policy": approval_policy,
            },
            on_progress=progress_cb,
            loop=asyncio.get_event_loop(),
        )

        async def terminal_execute_call() -> ToolResult:
            record_id = None
            if on_tool_start:
                record_id = on_tool_start(context.tool_name, context.tool_call_id, context.tool_args)

            try:
                loop = asyncio.get_event_loop()
                res = await asyncio.wait_for(
                    loop.run_in_executor(
                        _tool_thread_pool,
                        tool_registry.execute_tool_call,
                        context.tool_name,
                        context.tool_args,
                    ),
                    timeout=TOOL_TIMEOUT,
                )
                finish_status = "completed" if res.ok else "failed"
            except asyncio.TimeoutError:
                res = None
                finish_status = "timeout"
            except Exception:
                res = None
                finish_status = "failed"

            if on_tool_finish and record_id is not None:
                on_tool_finish(record_id, finish_status, res.content if res else None)
            return res

        res = await pipeline.execute(context, terminal_execute_call)
        return context, res

    # 5. 封装并发 Task 集合并启动
    tasks = []
    for tool_call in tool_calls:
        task = asyncio.create_task(run_single_tool(tool_call, [current_index]))
        tasks.append(task)

    gather_task = asyncio.ensure_future(asyncio.gather(*tasks))

    # 6. 流式事件流捕获主循环
    while True:
        if gather_task.done() and event_queue.empty():
            break

        queue_get_task = asyncio.create_task(event_queue.get())
        done, pending = await asyncio.wait(
            [gather_task, queue_get_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        if queue_get_task in done:
            progress_event = queue_get_task.result()
            progress_event.index = current_index
            current_index += 1
            yield progress_event
        else:
            queue_get_task.cancel()

        if gather_task.done():
            try:
                gather_task.result()
            except ApprovalRequiredException as exc:
                # 安全自愈：强行 cancel 其余尚在活跃状态的任务以阻断泄露
                for t in tasks:
                    if not t.done():
                        t.cancel()

                # 精准定位触发了审批拦截的具体工具及 ID
                failed_tool_name = None
                failed_tool_call_id = None
                for t in tasks:
                    if t.done() and not t.cancelled():
                        e = t.exception()
                        if isinstance(e, ApprovalRequiredException):
                            idx = tasks.index(t)
                            failed_tool_name = tool_calls[idx].function.name
                            failed_tool_call_id = tool_calls[idx].id
                            break

                yield AgentEvent(
                    index=current_index,
                    type="approval_required",
                    tool_name=failed_tool_name,
                    tool_call_id=failed_tool_call_id,
                    content=exc.approval_id,
                )
                current_index += 1
                yield ToolTurnResult(
                    events=[],
                    tool_messages=[],
                    next_event_index=current_index,
                    paused_for_approval=True,
                )
                return
            except Exception as exc:
                # 其它未知异常：强行 cancel 其余活跃任务并向上抛出
                for t in tasks:
                    if not t.done():
                        t.cancel()
                raise exc

    # 7. 并发结束，按时序合并输出最终卡片
    results = gather_task.result()
    for tool_call, (context, tool_result) in zip(tool_calls, results):
        if tool_result is None:
            error_message = f"Tool timed out after {TOOL_TIMEOUT}s"
            yield AgentEvent(
                index=current_index,
                type="tool_error",
                tool_name=tool_call.function.name,
                tool_call_id=tool_call.id,
                content=error_message,
            )
            tool_messages.append(
                ChatMessage(
                    role="tool",
                    tool_call_id=tool_call.id,
                    content=f"[TOOL_TIMEOUT] {error_message}",
                )
            )
        elif tool_result.ok:
            yield AgentEvent(
                index=current_index,
                type="tool_result",
                tool_name=tool_call.function.name,
                tool_call_id=tool_call.id,
                content=tool_result.content,
                tool_result=tool_result,
            )
            tool_messages.append(
                ChatMessage(
                    role="tool",
                    tool_call_id=tool_call.id,
                    content=tool_result.content,
                )
            )
        else:
            error_message = tool_result.error.message if tool_result.error else "Tool failed"
            yield AgentEvent(
                index=current_index,
                type="tool_error",
                tool_name=tool_call.function.name,
                tool_call_id=tool_call.id,
                content=error_message,
                tool_result=tool_result,
            )
            tool_messages.append(
                ChatMessage(
                    role="tool",
                    tool_call_id=tool_call.id,
                    content=f"[TOOL_ERROR] {error_message}",
                )
            )
        current_index += 1

    yield ToolTurnResult(
        events=[],
        tool_messages=tool_messages,
        next_event_index=current_index,
    )
