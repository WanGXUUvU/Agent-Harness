"""定义工具列表相关 HTTP 路由。"""

from fastapi import APIRouter
from backend.tools.build_registry import DEFAULT_TOOL_REGISTRY

router = APIRouter()


@router.get("/tools")
def list_tools_api():
    """获取全局默认注册表中的所有可用工具名称列表。"""
    return [{"name": name} for name in DEFAULT_TOOL_REGISTRY._tools.keys()]
