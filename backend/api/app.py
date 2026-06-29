"""创建并配置 FastAPI 应用。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.mcp.mcp_manager import get_mcp_server_manager
from .routes import router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    mcp_server_manager = get_mcp_server_manager()
    mcp_server_manager.start()
    try:
        yield
    finally:
        mcp_server_manager.stop()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
