"""工作区相关动作。"""

import os
from typing import Optional

from sqlalchemy.orm import Session

from backend.infra.db.orm_models import WorkspaceRecord
from backend.infra.os_proxy.apple_script import open_folder_dialog
from backend.workspace.store import SqliteWorkspaceStore


def list_workspaces(db: Session) -> list[WorkspaceRecord]:
    """返回所有已登记工作区。"""
    return SqliteWorkspaceStore(db).list_all()


def register_workspace(db: Session, path: str) -> WorkspaceRecord:
    """在缺失时登记一个本地工作区路径。"""
    abs_path = os.path.abspath(path)
    store = SqliteWorkspaceStore(db)
    existing = store.get_by_path(path=abs_path)
    if existing:
        return existing

    workspace_record = WorkspaceRecord(
        name=os.path.basename(abs_path),
        path=path,
    )
    store.save(workspace=workspace_record)
    db.commit()
    db.refresh(workspace_record)
    return workspace_record


def select_workspace_with_dialog(db: Session) -> Optional[WorkspaceRecord]:
    """打开原生目录选择框并登记所选工作区。"""
    selected_path = open_folder_dialog()
    if not selected_path:
        return None
    return register_workspace(
        db=db,
        path=selected_path,
    )
