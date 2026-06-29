"""模型服务商配置相关动作。"""

from typing import Optional

from sqlalchemy.orm import Session

from backend.infra.db.orm_models import ProviderConfig
from backend.settings.store import SqliteSettingsStore
from backend.settings.types import ProviderOut


def _provider_to_out(record: ProviderConfig) -> ProviderOut:
    key = record.api_key or ""
    hint = ("****" + key[-4:]) if len(key) >= 4 else ("*" * len(key)) if key else None
    return ProviderOut(
        id=record.id,
        name=record.name,
        base_url=record.base_url,
        api_key_hint=hint,
        created_at=record.created_at,
        is_default=bool(record.is_default),
    )


def create_provider(
    db: Session,
    name: str,
    base_url: str,
    api_key: str,
) -> ProviderOut:
    """创建或更新一条服务商配置。"""
    record = SqliteSettingsStore(db).create_provider(
        name=name,
        base_url=base_url,
        api_key=api_key,
    )
    db.commit()
    db.refresh(record)
    return _provider_to_out(record=record)


def list_providers(db: Session) -> list[ProviderOut]:
    """列出已配置的服务商。"""
    return [
        _provider_to_out(record=record)
        for record in SqliteSettingsStore(db).list_providers()
    ]


def patch_provider(
    db: Session,
    provider_id: int,
    *,
    name: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    is_default: Optional[bool] = None,
) -> ProviderOut:
    """更新一条服务商配置。"""
    record = SqliteSettingsStore(db).patch_provider(
        provider_id=provider_id,
        name=name,
        base_url=base_url,
        api_key=api_key,
        is_default=is_default,
    )
    if record is None:
        raise ValueError(f"Provider {provider_id} not found")
    db.commit()
    db.refresh(record)
    return _provider_to_out(record=record)


def delete_provider(db: Session, provider_id: int) -> None:
    """删除一条服务商配置。"""
    SqliteSettingsStore(db).delete_provider(provider_id=provider_id)
    db.commit()
