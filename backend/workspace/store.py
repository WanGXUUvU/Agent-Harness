"""工作区持久化。"""

from typing import Optional

from sqlalchemy.orm import Session

from backend.infra.db.orm_models import WorkspaceRecord


class SqliteWorkspaceStore:
    """已登记工作区的 SQLite 仓储。"""

    def __init__(self, db: Session):
        self.db = db

    def list_all(self) -> list[WorkspaceRecord]:
        """按创建时间倒序返回所有工作区。"""
        return (
            self.db.query(WorkspaceRecord)
            .order_by(WorkspaceRecord.created_at.desc())
            .all()
        )

    def get_by_path(self, path: str) -> Optional[WorkspaceRecord]:
        """按绝对路径返回一个工作区。"""
        return self.db.query(WorkspaceRecord).filter(WorkspaceRecord.path == path).first()

    def save(self, workspace: WorkspaceRecord) -> None:
        """暂存一条待持久化的工作区记录。"""
        self.db.add(workspace)
