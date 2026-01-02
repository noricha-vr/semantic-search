"""FastAPI メインアプリケーション。

ローカルドキュメント検索システムのREST APIを提供する。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import actions, documents, search
from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理。"""
    logger.info("Starting LocalDocSearch API server")
    yield
    logger.info("Shutting down LocalDocSearch API server")


app = FastAPI(
    title="LocalDocSearch API",
    description="ローカルドキュメント検索システムのAPI",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS設定（ローカル開発用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # SvelteKit dev server
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターを登録
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(actions.router, prefix="/api/actions", tags=["actions"])


@app.get("/")
async def root():
    """ルートエンドポイント。"""
    return {
        "name": "LocalDocSearch API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    """ヘルスチェックエンドポイント。"""
    return {"status": "healthy"}


def run_server():
    """開発サーバーを起動。"""
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )


if __name__ == "__main__":
    run_server()
