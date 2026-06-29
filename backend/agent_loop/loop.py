"""智能体运行的核心 Loop 状态机引擎。"""

from typing import AsyncIterator, Optional, Union

from backend.agent.types import AgentDefinition, DEFAULT_AGENT_DEFINITION
from backend.core.types import (
    StreamChunk,
    ModelAdapter,
)
from backend.agent_loop.types import RunEvent, RunState, RunInput, RunOutput
from backend.agent_loop.handle_tool_calls import VfsProvider
from backend.security.policy.types import ApprovalPolicy
from backend.tools.build_registry import DEFAULT_TOOL_REGISTRY
from backend.tools.registry import ToolRegistry
from backend.agent_loop.run_agent import run_agent
from backend.agent_loop.stream_agent import stream_agent


class AgentLoop:
    """智能体运行的核心 Loop（状态机）。"""

    def __init__(
        self,
        state: Optional[RunState] = None,
        agent_profile: Optional[AgentDefinition] = None,
        runtime_system_prompt: Optional[str] = None,
        tool_registry: Optional[ToolRegistry] = None,
        model_adapter: Optional[ModelAdapter] = None,
        approval_policy: ApprovalPolicy = ApprovalPolicy.NEVER,
        vfs_provider: Optional[VfsProvider] = None,
    ):
        self.state = state or RunState()
        self.agent_profile = agent_profile or DEFAULT_AGENT_DEFINITION
        self.runtime_system_prompt = (
            runtime_system_prompt
            if runtime_system_prompt is not None
            else self.agent_profile.system_prompt
        )
        self.tool_registry = tool_registry or DEFAULT_TOOL_REGISTRY
        self.model_adapter = model_adapter
        self.approval_policy = approval_policy
        self.vfs_provider = vfs_provider
        self.last_usage = None

    def run_sync(self, run_input: RunInput, run_id: Optional[str] = None) -> RunOutput:
        """同步运行模式：一次性执行到底。"""
        return run_agent(
            loop=self,
            run_input=run_input,
            run_id=run_id,
        )

    async def stream(
        self,
        run_input: RunInput,
        skip_user_message: bool = False,
        event_index: int = 0,
        run_id: Optional[str] = None,
        workspace_path: Optional[str] = None,
    ) -> AsyncIterator[Union[RunEvent, str, StreamChunk]]:
        """流式异步运行模式，逐帧产生 Token 或引擎状态事件。"""
        async for item in stream_agent(
            loop=self,
            run_input=run_input,
            skip_user_message=skip_user_message,
            event_index=event_index,
            run_id=run_id,
            workspace_path=workspace_path,
        ):
            yield item
