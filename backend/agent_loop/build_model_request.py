"""把循环状态组装成模型请求。"""

from backend.agent.types import AgentDefinition
from backend.agent_loop.types import RunState
from backend.core.types import ChatMessage, ModelConfig, ModelRequest
from backend.tools.registry import ToolRegistry


def build_model_request(
    *,
    agent_profile: AgentDefinition,
    runtime_system_prompt: str,
    state: RunState,
    tool_registry: ToolRegistry,
) -> ModelRequest:
    """把提示词、历史和工具 schema 打包成模型请求。"""
    return ModelRequest(
        messages=[
            ChatMessage(role="system", content=runtime_system_prompt),
            *state.messages,
        ],
        tools=tool_registry.get_tool_schemas(agent_profile.tool_names),
        config=ModelConfig(
            model=None,
            stream=False,
        ),
    )
