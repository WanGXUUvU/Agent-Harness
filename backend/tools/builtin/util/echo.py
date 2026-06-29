"""定义回显测试工具。"""

from backend.tools.types import ToolDefinition
from backend.tools.result_types import ToolResult
from backend.tools.types import RiskLevel


def echo_tool(text: str) -> ToolResult:
    """回显输入文本。"""
    # 这是本地真正执行的工具逻辑。
    # 模型只会返回 tool_calls，真正的函数执行发生在这里。
    return ToolResult(
        ok=True,
        content=f"tool received:{text}",
        metadata={"tool_name": "echo_tool"},
    )


ECHO_TOOL_SCHEMA = {  # 给模型看的工具说明
    "type": "function",
    "function": {
        "name": "echo_tool",
        "description": "Echo the input text back to the caller",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to echo back.",
                }
            },
            "required": ["text"],
            "additionalProperties": False,
        },
    },
}


def build_echo_tool_definition() -> ToolDefinition:  # 构造注册对象
    """构建回显工具定义。"""
    return ToolDefinition(
        name="echo_tool",  # 工具名
        schema=ECHO_TOOL_SCHEMA,  # schema
        handler=echo_tool,  # 执行函数
        risk_level=RiskLevel.SAFE,
    )
