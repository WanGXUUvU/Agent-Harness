"""处理 MCP 服务配置相关动作。"""

from backend.mcp.mcp_manager import get_mcp_server_manager
from backend.mcp.settings import (
    build_mcp_server_config,
    get_mcp_servers,
    save_mcp_servers,
)


def _normalize_raw_server(raw_server: dict) -> dict:
    transport = raw_server.get("transport")
    normalized = {
        "server_id": raw_server.get("server_id"),
        "display_name": raw_server.get("display_name"),
        "transport": transport,
        "enabled": raw_server.get("enabled", True),
        "required": raw_server.get("required", False),
        "startup_timeout_sec": raw_server.get("startup_timeout_sec", 10),
        "tool_timeout_sec": raw_server.get("tool_timeout_sec", 30),
    }

    if transport == "stdio":
        normalized["command"] = raw_server.get("command")
        normalized["args"] = raw_server.get("args", [])
        normalized["env"] = raw_server.get("env", {})
        normalized["cwd"] = raw_server.get("cwd")
        return normalized

    if transport == "streamable_http":
        normalized["url"] = raw_server.get("url")
        normalized["bearer_token"] = raw_server.get("bearer_token")
        normalized["http_headers"] = raw_server.get("http_headers", {})
        return normalized

    return normalized


def _validate_raw_server(raw_server: dict) -> dict:
    normalized = _normalize_raw_server(raw_server=raw_server)
    build_mcp_server_config(raw_config=normalized)
    return normalized


def _find_server_index(servers: list[dict], server_id: str) -> int:
    for index, server in enumerate(servers):
        if server.get("server_id") == server_id:
            return index
    raise LookupError(f"MCP server {server_id} not found")


def _build_runtime_info(raw_server: dict) -> dict:
    enabled = raw_server.get("enabled", True)
    if not enabled:
        return {
            "runtime_status": "disabled",
            "tool_count": 0,
            "last_error": None,
        }

    manager = get_mcp_server_manager()
    if not manager.is_started():
        return {
            "runtime_status": "not_started",
            "tool_count": 0,
            "last_error": None,
        }

    runtime_snapshot = manager.get_runtime_snapshot()
    return runtime_snapshot.get(
        raw_server.get("server_id"),
        {
            "runtime_status": "not_started",
            "tool_count": 0,
            "last_error": None,
        },
    )


def _build_server_out(raw_server: dict) -> dict:
    normalized = _validate_raw_server(raw_server=raw_server)
    runtime_info = _build_runtime_info(raw_server=normalized)
    return {
        "server_id": normalized["server_id"],
        "display_name": normalized.get("display_name"),
        "transport": normalized["transport"],
        "enabled": normalized["enabled"],
        "required": normalized["required"],
        "startup_timeout_sec": normalized["startup_timeout_sec"],
        "tool_timeout_sec": normalized["tool_timeout_sec"],
        "command": normalized.get("command"),
        "args": normalized.get("args", []),
        "env": normalized.get("env", {}),
        "cwd": normalized.get("cwd"),
        "url": normalized.get("url"),
        "bearer_token": normalized.get("bearer_token"),
        "http_headers": normalized.get("http_headers", {}),
        "runtime_status": runtime_info["runtime_status"],
        "tool_count": runtime_info["tool_count"],
        "last_error": runtime_info["last_error"],
    }


def list_servers() -> list[dict]:
    """列出 MCP 服务及其运行时状态。"""
    return [_build_server_out(raw_server=server) for server in get_mcp_servers()]


def get_server(server_id: str) -> dict:
    """读取一条 MCP 服务配置。"""
    servers = get_mcp_servers()
    return _build_server_out(
        raw_server=servers[_find_server_index(servers=servers, server_id=server_id)]
    )


def create_server(payload: dict) -> dict:
    """创建一条 MCP 服务配置。"""
    servers = get_mcp_servers()
    server_id = payload.get("server_id")
    for server in servers:
        if server.get("server_id") == server_id:
            raise ValueError(f"MCP server {server_id} already exists")

    normalized = _validate_raw_server(raw_server=payload)
    servers.append(normalized)
    save_mcp_servers(servers=servers)
    return _build_server_out(raw_server=normalized)


def patch_server(server_id: str, payload: dict) -> dict:
    """更新一条 MCP 服务配置。"""
    servers = get_mcp_servers()
    server_index = _find_server_index(servers=servers, server_id=server_id)
    merged = dict(servers[server_index])
    merged.update(payload)
    merged["server_id"] = server_id
    normalized = _validate_raw_server(raw_server=merged)
    servers[server_index] = normalized
    save_mcp_servers(servers=servers)
    return _build_server_out(raw_server=normalized)


def delete_server(server_id: str) -> None:
    """删除一条 MCP 服务配置。"""
    servers = get_mcp_servers()
    del servers[_find_server_index(servers=servers, server_id=server_id)]
    save_mcp_servers(servers=servers)


def reload_runtime() -> dict:
    """按当前配置重载 MCP 运行时。"""
    manager = get_mcp_server_manager()
    manager.reload()

    runtime_snapshot = manager.get_runtime_snapshot()
    errors = []
    connected_servers = 0

    for server_id, info in runtime_snapshot.items():
        if info["runtime_status"] == "connected":
            connected_servers += 1
        elif info["runtime_status"] == "error":
            errors.append(
                {
                    "server_id": server_id,
                    "message": info["last_error"] or "Unknown MCP error",
                }
            )

    return {
        "ok": True,
        "connected_servers": connected_servers,
        "failed_servers": len(errors),
        "errors": errors,
    }
