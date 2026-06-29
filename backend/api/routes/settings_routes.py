"""定义设置相关 HTTP 路由。"""

from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.api.dto.schemas import (
    CreateProviderInput,
    CreateMcpServerInput,
    McpReloadOut,
    McpServerOut,
    PatchModelInput,
    PatchMcpServerInput,
    PatchProviderInput,
)
from backend.api.routes.dependencies import error_response
from backend.infra.db.engine import get_db
from backend.infra.config.settings import load_settings, save_settings
from backend.mcp.servers import (
    create_server,
    delete_server,
    get_server,
    list_servers,
    patch_server,
    reload_runtime,
)
from backend.settings import ModelOut, ProviderOut
from backend.settings.models import list_models, patch_model, sync_provider_models
from backend.settings.providers import (
    create_provider,
    delete_provider,
    list_providers,
    patch_provider,
)

router = APIRouter(prefix="/settings")


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


@router.post(
    "/providers", response_model=ProviderOut, status_code=status.HTTP_201_CREATED
)
def create_provider_api(
    payload: CreateProviderInput,
    db: Session = Depends(get_db),
) -> ProviderOut:
    """注册并添加一个新的模型服务商配置。"""
    return create_provider(
        db=db,
        name=payload.name,
        base_url=payload.base_url,
        api_key=payload.api_key,
    )


@router.get("/providers", response_model=list[ProviderOut])
def list_providers_api(
    db: Session = Depends(get_db),
) -> list[ProviderOut]:
    """列出系统里所有已注册的大模型供应商列表。"""
    return list_providers(db=db)


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider_api(
    provider_id: int,
    db: Session = Depends(get_db),
) -> None:
    """物理删除指定 ID 的大模型供应商记录。"""
    delete_provider(
        db=db,
        provider_id=provider_id,
    )


@router.patch("/providers/{provider_id}", response_model=ProviderOut)
def patch_provider_api(
    provider_id: int,
    payload: PatchProviderInput,
    db: Session = Depends(get_db),
) -> ProviderOut:
    """更新指定大模型供应商的属性（名字、接口地址、API 密钥等）。"""
    try:
        return patch_provider(
            db=db,
            provider_id=provider_id,
            name=payload.name,
            base_url=payload.base_url,
            api_key=payload.api_key,
            is_default=payload.is_default,
        )
    except ValueError as exc:
        return error_response(status.HTTP_404_NOT_FOUND, "provider_not_found", str(exc))


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


@router.get("/providers/{provider_id}/models", response_model=list[ModelOut])
def sync_provider_models_api(
    provider_id: int,
    db: Session = Depends(get_db),
) -> list[ModelOut]:
    """请求供应商的 models 接口同步其所支持的所有可用文本模型到本地数据库。"""
    try:
        return sync_provider_models(
            db=db,
            provider_id=provider_id,
        )
    except ValueError as exc:
        return error_response(status.HTTP_404_NOT_FOUND, "provider_not_found", str(exc))


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


@router.get("/models", response_model=list[ModelOut])
def list_models_api(
    provider_id: Optional[int] = None,
    enabled: Optional[bool] = None,
    db: Session = Depends(get_db),
) -> list[ModelOut]:
    """列出本地数据库保存的所有已同步模型列表，支持按供应商或启用状态过滤。"""
    return list_models(
        db=db,
        provider_id=provider_id,
        enabled_only=enabled is True,
    )


@router.patch("/models/{model_id}", response_model=ModelOut)
def patch_model_api(
    model_id: int,
    payload: PatchModelInput,
    db: Session = Depends(get_db),
) -> ModelOut:
    """修改指定模型的启用状态或在界面上的显示名称（中文别名）。"""
    try:
        return patch_model(
            db=db,
            model_db_id=model_id,
            enabled=payload.enabled,
            display_name=payload.display_name,
        )
    except ValueError as exc:
        return error_response(status.HTTP_404_NOT_FOUND, "model_not_found", str(exc))


# ---------------------------------------------------------------------------
# MCP Servers
# ---------------------------------------------------------------------------


@router.get("/mcp/servers", response_model=list[McpServerOut])
def list_mcp_servers_api() -> list[McpServerOut]:
    """列出全部 MCP 服务配置摘要及其运行时状态。"""
    return list_servers()


@router.get("/mcp/servers/{server_id}", response_model=McpServerOut)
def get_mcp_server_api(
    server_id: str,
) -> McpServerOut:
    """读取单条 MCP 服务详情。"""
    try:
        return get_server(server_id=server_id)
    except LookupError as exc:
        return error_response(status.HTTP_404_NOT_FOUND, "mcp_server_not_found", str(exc))


@router.post(
    "/mcp/servers",
    response_model=McpServerOut,
    status_code=status.HTTP_201_CREATED,
)
def create_mcp_server_api(
    payload: CreateMcpServerInput,
) -> McpServerOut:
    """新增一条 MCP 服务配置。"""
    try:
        return create_server(payload=payload.model_dump())
    except ValueError as exc:
        return error_response(status.HTTP_400_BAD_REQUEST, "invalid_mcp_server", str(exc))


@router.patch("/mcp/servers/{server_id}", response_model=McpServerOut)
def patch_mcp_server_api(
    server_id: str,
    payload: PatchMcpServerInput,
) -> McpServerOut:
    """局部更新一条 MCP 服务配置。"""
    try:
        return patch_server(
            server_id=server_id,
            payload=payload.model_dump(exclude_unset=True),
        )
    except LookupError as exc:
        return error_response(status.HTTP_404_NOT_FOUND, "mcp_server_not_found", str(exc))
    except ValueError as exc:
        return error_response(status.HTTP_400_BAD_REQUEST, "invalid_mcp_server", str(exc))


@router.delete("/mcp/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mcp_server_api(
    server_id: str,
) -> None:
    """删除一条 MCP 服务配置。"""
    try:
        delete_server(server_id=server_id)
    except LookupError as exc:
        return error_response(status.HTTP_404_NOT_FOUND, "mcp_server_not_found", str(exc))


@router.post("/mcp/reload", response_model=McpReloadOut)
def reload_mcp_runtime_api() -> McpReloadOut:
    """按最新 settings.json 重新启动 MCP 运行时。"""
    try:
        return reload_runtime()
    except Exception as exc:
        return error_response(status.HTTP_400_BAD_REQUEST, "mcp_reload_failed", str(exc))


# ---------------------------------------------------------------------------
# Settings.json File Management
# ---------------------------------------------------------------------------

@router.get("/file")
def get_settings_file_api() -> dict:
    """获取完整的 settings.json 配置数据。"""
    return load_settings()


@router.post("/file")
def update_settings_file_api(payload: dict) -> dict:
    """更新完整的 settings.json 配置数据。"""
    save_settings(data=payload)
    return {"status": "success"}
