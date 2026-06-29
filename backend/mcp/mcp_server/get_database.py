"""提供本地数据库只读访问的 MCP 服务。"""

import os

from mcp.server.fastmcp import FastMCP
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

mcp = FastMCP("get_local_data")

# The database URL is injected by the MCP host process through stdio env.
DATABASEURL_URL = os.getenv("DATABASE_URL", "")

engine = create_engine(
    DATABASEURL_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@mcp.tool()
def get_tables() -> list[str]:
    """返回当前数据库里的所有表名。"""

    inspector = inspect(engine)
    return inspector.get_table_names()


@mcp.tool()
def get_table_columns(table_name: str) -> list[str]:
    """返回指定数据表的所有列名。"""

    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    if table_name not in table_names:
        raise ValueError(f"table not found: {table_name}")

    return [column["name"] for column in inspector.get_columns(table_name)]


if __name__ == "__main__":
    mcp.run(transport="stdio")
