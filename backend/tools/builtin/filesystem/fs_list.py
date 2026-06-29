"""定义列目录工具并执行目录遍历。"""

from backend.tools.types import ToolDefinition
from backend.tools.types import RiskLevel
from backend.tools.result_types import ToolResult
from pathlib import Path


def list_dir(path: str) -> ToolResult:
    """列出目录内容。"""
    target = Path(path)

    if not target.exists():
        raise ValueError(f"Directory not found :{path}")

    if not target.is_dir():
        raise ValueError(f"Not a directory: {path}")
    items = sorted(child.name for child in target.iterdir())
    return ToolResult(
        ok=True,
        content="\n".join(items),
        metadata={"tool_name": "list_dir", "path": path},
    )


LIST_DIR_SCHEMA = {  # 给模型看的工具说明
    "type": "function",
    "function": {
        "name": "list_dir",
        "description": "List files and folders in a directory",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list",
                }
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
}


def build_list_dir_definition() -> ToolDefinition:
    """构建列目录工具定义。"""
    return ToolDefinition(
        name="list_dir",
        schema=LIST_DIR_SCHEMA,
        handler=list_dir,
        risk_level=RiskLevel.SAFE,
    )
