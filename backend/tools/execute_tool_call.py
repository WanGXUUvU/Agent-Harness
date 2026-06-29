"""执行单次工具调用。"""

import inspect
import json
from typing import Any, Optional

from backend.sandbox.resolver import SandboxPathResolver
from backend.tools.result_types import ToolError, ToolResult


def execute_tool_call(
    registry,
    name: str,
    arguments: str,
    context: Optional[Any] = None,
) -> ToolResult:
    """解析参数、执行沙箱改写并调用单个工具 handler。"""
    workspace_path = getattr(context, "workspace_path", None)

    if workspace_path:
        ok, modified_args, err_msg = SandboxPathResolver.resolve_and_rewrite(
            name,
            arguments,
            workspace_path,
        )
        if not ok:
            return ToolResult(
                ok=False,
                error=ToolError(
                    code="SANDBOX_VIOLATION",
                    tool_name=name,
                    message=err_msg or "Sandbox Violation",
                ),
                metadata={"tool_name": name},
            )
        arguments = modified_args

    tool = registry._tools.get(name)
    if tool is None:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="unknown_tool",
                tool_name=name,
                message=f"Unknown tool: {name}",
            ),
            metadata={"tool_name": name},
        )

    try:
        args = json.loads(arguments or "{}")
    except json.JSONDecodeError as exc:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="invalid_arguments",
                tool_name=name,
                message="Invalid JSON arguments",
            ),
            metadata={
                "tool_name": name,
                "raw_arguments": arguments,
                "debug": str(exc),
            },
        )

    try:
        signature = inspect.signature(tool.handler)
        if "__context__" in signature.parameters:
            args["__context__"] = context
        result = tool.handler(**args)
    except TypeError as exc:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="invalid_arguments",
                tool_name=name,
                message=str(exc),
            ),
            metadata={"tool_name": name},
        )
    except Exception as exc:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="tool_runtime_error",
                tool_name=name,
                message=str(exc),
            ),
            metadata={"tool_name": name},
        )

    if not isinstance(result, ToolResult):
        return ToolResult(
            ok=False,
            error=ToolError(
                code="invalid_tool_result",
                tool_name=name,
                message=f"Tool {name} must return ToolResult",
            ),
            metadata={"tool_name": name},
        )

    return result
