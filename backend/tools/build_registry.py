"""组装默认工具和运行时工具注册表。"""

from typing import Callable

from backend.mcp.bridge import build_mcp_tool_definitions
from backend.mcp.mcp_manager import get_mcp_server_manager
from backend.tools.builtin.agent_bridge.check_child_status import (
    build_check_child_status_tool,
)
from backend.tools.builtin.agent_bridge.spawn_child_agent import (
    build_spawn_child_agent_tool,
)
from backend.tools.builtin.agent_bridge.wait_child_agent import (
    build_wait_child_agent_tool,
)
from backend.tools.builtin.filesystem.fs_list import build_list_dir_definition
from backend.tools.builtin.filesystem.fs_read import build_read_file_tool_definition
from backend.tools.builtin.filesystem.fs_search import build_search_text_definition
from backend.tools.builtin.filesystem.fs_write import build_write_file_tool_definition
from backend.tools.builtin.search.web_search import build_web_search_tool_definition
from backend.tools.builtin.util.echo import build_echo_tool_definition
from backend.tools.registry import ToolRegistry


def build_default_tool_registry() -> ToolRegistry:
    """构建静态默认工具注册表。"""
    registry = ToolRegistry()

    # 1. 文件系统工具
    registry.register(build_read_file_tool_definition())
    registry.register(build_list_dir_definition())
    registry.register(build_write_file_tool_definition())
    registry.register(build_search_text_definition())

    # 2. 通用工具
    registry.register(build_echo_tool_definition())

    # 3. 外部搜索工具
    registry.register(build_web_search_tool_definition())
    return registry


def build_run_registry(
    *,
    child_dispatcher: Callable[[str, str], str],
    status_checker: Callable[[list[str]], dict],
    child_waiter: Callable[[str], str],
) -> ToolRegistry:
    """构建单次运行专属的工具注册表。"""
    # 1. 从不可变默认注册表克隆一份
    registry = DEFAULT_TOOL_REGISTRY.clone()

    # 2. 追加当前进程发现到的 MCP 工具
    mcp_server_manager = get_mcp_server_manager()
    try:
        discovered_mcp_tools = mcp_server_manager.list_all_tools()
    except RuntimeError as exc:
        print(f"[MCP] skip tool registration: {exc}")
        discovered_mcp_tools = []

    for tool in build_mcp_tool_definitions(discovered_mcp_tools):
        registry.register(tool)

    # 3. 追加本轮运行专属的子 Agent 工具
    registry.register(build_spawn_child_agent_tool(child_dispatcher))
    registry.register(build_check_child_status_tool(status_checker))
    registry.register(build_wait_child_agent_tool(child_waiter))
    return registry


DEFAULT_TOOL_REGISTRY = build_default_tool_registry()
