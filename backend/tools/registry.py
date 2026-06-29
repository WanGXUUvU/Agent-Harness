"""管理工具注册和执行入口。"""

from typing import Any, Optional

from backend.tools.execute_tool_call import execute_tool_call
from backend.tools.types import RiskLevel, ToolDefinition


class ToolRegistry:
    """工具定义注册表容器。"""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def clone(self) -> "ToolRegistry":
        """克隆当前注册表映射。"""
        new = ToolRegistry()
        new._tools = dict(self._tools)
        return new

    def register(self, tool: ToolDefinition) -> None:
        """注册一个工具定义。"""
        self._tools[tool.name] = tool

    def get_tool_schemas(self, tool_names: Optional[list[str]] = None) -> list[dict]:
        """返回工具 JSON schema 列表。"""
        if tool_names is None:
            tools = self._tools.values()
        else:
            tools = [self._tools[name] for name in tool_names if name in self._tools]
        return [tool.schema for tool in tools]

    def get_risk_level(self, name: str) -> RiskLevel:
        """返回工具风险等级。"""
        tool = self._tools.get(name)
        if tool is None:
            return RiskLevel.SAFE
        return tool.risk_level

    def execute_tool_call(
        self,
        name: str,
        arguments: str,
        context: Optional[Any] = None,
    ):
        """执行一个已注册工具。"""
        return execute_tool_call(self, name, arguments, context)

__all__ = ["ToolRegistry"]
