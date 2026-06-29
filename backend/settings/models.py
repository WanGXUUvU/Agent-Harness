"""模型配置相关动作。"""

import json
import re
from typing import Optional

import requests
from sqlalchemy.orm import Session

from backend.infra.db.orm_models import ModelSetting, ProviderConfig
from backend.prompt.strategies.thinking import get_effort_levels
from backend.settings.store import SqliteSettingsStore
from backend.settings.types import ModelOut


def _model_to_out(record: ModelSetting) -> ModelOut:
    return ModelOut(
        id=record.id,
        provider_id=record.provider_id,
        model_id=record.model_id,
        display_name=record.display_name,
        enabled=bool(record.enabled),
        supports_thinking=bool(record.supports_thinking),
        thinking_style=record.thinking_style,
        effort_levels=json.loads(record.effort_levels or "[]"),
        context_length=record.context_length,
        supports_tools=bool(record.supports_tools),
    )


def list_models(
    db: Session,
    *,
    provider_id: Optional[int] = None,
    enabled_only: bool = False,
) -> list[ModelOut]:
    """列出本地模型配置。"""
    return [
        _model_to_out(record=record)
        for record in SqliteSettingsStore(db).list_models(
            provider_id=provider_id,
            enabled_only=enabled_only,
        )
    ]


def patch_model(
    db: Session,
    model_db_id: int,
    *,
    enabled: Optional[bool] = None,
    display_name: Optional[str] = None,
) -> ModelOut:
    """更新一条本地模型配置。"""
    enabled_int = int(enabled) if enabled is not None else None
    record = SqliteSettingsStore(db).patch_model(
        model_db_id=model_db_id,
        enabled=enabled_int,
        display_name=display_name,
    )
    if record is None:
        raise ValueError(f"ModelSetting {model_db_id} not found")
    db.commit()
    db.refresh(record)
    return _model_to_out(record=record)


def infer_thinking_style(model_id: str, supported_features: list[str]) -> str:
    """根据模型元数据推断 thinking 风格。"""
    model_name = model_id.lower()
    has_reasoning = "reasoning" in supported_features

    if has_reasoning:
        if "deepseek" in model_name:
            return "deepseek_style"
        if "moonshot" in model_name or "kimi" in model_name:
            return "kimi_style"
        if "glm" in model_name or "z1" in model_name:
            return "glm_style"
        return "sensenova_style"

    if "claude" in model_name and "haiku" not in model_name:
        return "claude_style"
    if "deepseek" in model_name:
        return "deepseek_style"
    if "qwq" in model_name or "qwen3" in model_name:
        return "qwen_style"
    if ("kimi" in model_name or "moonshot" in model_name) and "-k" in model_name:
        return "kimi_style"
    if "openai-o" in model_name or re.match(r"^o\d", model_name):
        return "deepseek_style"
    if re.match(r"openai-gpt-5\.[1-9]", model_name):
        return "openai_style"
    if re.match(r"openai-gpt-[5-9]", model_name):
        return "deepseek_style"
    if "minimax" in model_name and re.search(r"m[2-9]", model_name):
        return "always_on_style"
    return "none"


def sync_provider_models(db: Session, provider_id: int) -> list[ModelOut]:
    """从服务商拉取模型并更新本地配置。"""
    provider = db.query(ProviderConfig).filter(ProviderConfig.id == provider_id).first()
    if provider is None:
        raise ValueError(f"Provider {provider_id} not found")

    response = requests.get(
        f"{provider.base_url.rstrip('/')}/models",
        headers={"Authorization": f"Bearer {provider.api_key}"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json().get("data", [])
    store = SqliteSettingsStore(db)
    results = []

    for item in data:
        model_id = item.get("id", "")
        output_modalities = item.get("output_modalities") or []
        if "image" in output_modalities:
            continue

        supported_features = item.get("supported_features") or []
        thinking_style = infer_thinking_style(
            model_id=model_id,
            supported_features=supported_features,
        )
        supports_thinking = thinking_style != "none"
        record = store.upsert_model(
            provider_id=provider_id,
            model_id=model_id,
            display_name=item.get("display_name") or model_id,
            supports_thinking=supports_thinking,
            thinking_style=thinking_style,
            effort_levels=json.dumps(get_effort_levels(thinking_style)),
            context_length=item.get("context_length"),
            supports_tools="tools" in supported_features,
        )
        results.append(record)

    db.commit()
    return [_model_to_out(record=record) for record in results]
