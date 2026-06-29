"""组装单次运行专属的智能体循环。"""

from backend.agent.types import AgentDefinition
from backend.agent_loop.loop import AgentLoop
from backend.core.adapters.chat_completions import ChatCompletionsAdapter
from backend.run.child.launcher import (
    create_child_launcher,
    create_child_status_checker,
    create_child_waiter,
)
from backend.run.runtime.vfs import RunVfsRegistry
from backend.security.policy.types import ApprovalPolicy
from backend.tools.build_registry import build_run_registry
from backend.agent_loop.types import RunState


def build_run_tool_registry(
    *,
    run_id: str,
    session_id: str,
):
    """构建单次运行专属的工具注册表。"""
    return build_run_registry(
        child_dispatcher=create_child_launcher(
            parent_run_id=run_id,
            session_id=session_id,
        ),
        status_checker=create_child_status_checker(),
        child_waiter=create_child_waiter(),
    )


def build_agent_loop(
    *,
    run_id: str,
    session_id: str,
    state: RunState,
    agent_profile: AgentDefinition,
    runtime_system_prompt: str,
    model_adapter: ChatCompletionsAdapter,
    approval_policy: ApprovalPolicy,
) -> AgentLoop:
    """构建单次运行专属的智能体循环。"""
    tool_registry = build_run_tool_registry(
        run_id=run_id,
        session_id=session_id,
    )
    return AgentLoop(
        state=state,
        agent_profile=agent_profile,
        runtime_system_prompt=runtime_system_prompt,
        model_adapter=model_adapter,
        tool_registry=tool_registry,
        approval_policy=approval_policy,
        vfs_provider=RunVfsRegistry.get,
    )
