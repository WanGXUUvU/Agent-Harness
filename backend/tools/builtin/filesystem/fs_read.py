"""定义读文件工具并执行文件读取。"""

from pathlib import Path  # 方便处理文件路径
from backend.tools.types import ToolDefinition  # 导入工具定义
from backend.tools.types import RiskLevel
from backend.tools.result_types import ToolResult


def read_file(path: str, __context__=None) -> ToolResult:
    """读取文件内容，优先命中 VFS 暂存区。"""
    # 🟢 优先检查 VFS 暂存区（可能有本次 Run 中其他工具刚暂存的新内容）
    vfs = None
    if __context__ is not None:
        vfs = __context__.vfs
    if vfs is not None:
        try:
            # 🟢 委托给 VFS 处理：命中返回暂存内容，标记删除则抛 FileNotFoundError，未暂存则降级读磁盘
            return ToolResult(
                ok=True,
                content=vfs.read_text(path),
                metadata={"tool_name": "read_file", "path": path},
            )
        except FileNotFoundError as exc:
            raise ValueError(f"File not found: {path}") from exc
    # 🔴 降级：没有 VFS，走原有的物理磁盘读取逻辑
    target = Path(path)
    if not target.exists():
        raise ValueError(f"File not found: {path}")
    if not target.is_file():
        raise ValueError(f"Not a file: {path}")
    return ToolResult(
        ok=True,
        content=target.read_text(encoding="utf-8"),
        metadata={"tool_name": "read_file", "path": path},
    )


READ_FILE_SCHEMA = {  # 给模型看的说明
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read the content of a file",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file",
                }
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
}


def build_read_file_tool_definition() -> ToolDefinition:  # 构造注册对象
    """构建读文件工具定义。"""
    return ToolDefinition(
        name="read_file",  # 工具名
        schema=READ_FILE_SCHEMA,  # schema
        handler=read_file,  # 真正执行逻辑
        risk_level=RiskLevel.SAFE,
    )
