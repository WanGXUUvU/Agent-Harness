"""定义工具执行结果类型。"""

from typing import Any, Optional
from enum import Enum

from pydantic import BaseModel, Field


class ToolError(BaseModel):
    """工具失败时返回给上层的结构化错误。"""

    ok: bool = False
    code: str
    tool_name: str
    message: str


class ToolResult(BaseModel):
    """统一的工具执行结果。"""

    ok: bool
    content: Optional[str] = None
    error: Optional[ToolError] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolState(str, Enum):
    """工具写入的vfs状态。"""

    STAGED = "staged"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
