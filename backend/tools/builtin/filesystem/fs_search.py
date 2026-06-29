"""定义搜索文本工具并执行文件检索。"""

from backend.tools.types import ToolDefinition
from backend.tools.types import RiskLevel
from backend.tools.result_types import ToolResult
from pathlib import Path


def _is_within_directory(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def search_text(query: str, path: str = ".", __context__=None) -> ToolResult:
    """搜索目录下文件内容，包含 VFS 暂存结果。"""
    target = Path(path)

    if not target.exists():
        raise ValueError(f"Path not found: {path}")

    if not target.is_dir():
        raise ValueError(f"Not a directory: {path}")

    # 🟢 尝试从 context 拿到 VFS 实例
    vfs = None
    if __context__ is not None:
        vfs = __context__.vfs

    matches = []
    target_root = target.resolve()

    # ── A. 扫物理磁盘文件 ────────────────────────────────────────
    for file_path in target.rglob("*"):
        if not file_path.is_file():
            continue

        # 🟢 跳过 VFS 中标记为删除的文件（逻辑上已不存在）
        if vfs is not None and not vfs.exists(str(file_path)):
            continue

        try:
            # 🟢 读文件时优先走 VFS（有暂存内容就用暂存内容，否则读磁盘）
            content = (
                vfs.read_text(str(file_path))
                if vfs
                else file_path.read_text(encoding="utf-8")
            )
        except (UnicodeDecodeError, FileNotFoundError):
            continue

        for line_no, line in enumerate(content.splitlines(), start=1):
            if query in line:
                matches.append(f"{file_path}:{line_no}: {line.strip()}")

    # ── B. 叠加扫 VFS 暂存区里的全新文件（物理磁盘上还不存在的） ──
    if vfs is not None:
        for staged_path, staged_content in vfs.staged_writes.items():
            staged_file = Path(staged_path)
            if not _is_within_directory(target_root, staged_file):
                continue
            if staged_file.exists():
                continue

            for line_no, line in enumerate(staged_content.splitlines(), start=1):
                if query in line:
                    matches.append(f"{staged_path}:{line_no}: {line.strip()}")

    return ToolResult(
        ok=True,
        content="\n".join(matches) if matches else f"No matches for: {query}",
        metadata={"tool_name": "search_text", "query": query, "path": path},
    )


SEARCH_TEXT_SCHEMA = {  # 给模型看的工具说明
    "type": "function",
    "function": {
        "name": "search_text",  # 工具名
        "description": "Search text in files under a directory",  # 工具描述
        "parameters": {
            "type": "object",
            "properties": {
                "query": {  # 搜索关键字
                    "type": "string",
                    "description": "Text to search for",
                },
                "path": {  # 搜索目录
                    "type": "string",
                    "description": "Directory path to search in",
                    "default": ".",
                },
            },
            "required": ["query"],  # query 必填
            "additionalProperties": False,  # 不允许多余参数
        },
    },
}


def build_search_text_definition() -> ToolDefinition:
    """构建文本搜索工具定义。"""
    return ToolDefinition(
        name="search_text",
        schema=SEARCH_TEXT_SCHEMA,
        handler=search_text,
        risk_level=RiskLevel.SAFE,
    )
