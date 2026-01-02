"""FastAPI メインアプリケーション。

ローカルドキュメント検索システムのREST APIを提供する。
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes import actions, documents, search
from src.config.logging import get_logger
from src.config.settings import get_settings
from src.utils.errors import LocalDocSearchError, to_http_exception

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

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # SvelteKit dev server
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://ms25:2602",
        "http://localhost:2602",
        "http://127.0.0.1:2602",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# グローバルエラーハンドラ
@app.exception_handler(LocalDocSearchError)
async def local_doc_search_error_handler(
    request: Request, exc: LocalDocSearchError
) -> JSONResponse:
    """カスタムエラーをJSONレスポンスに変換。"""
    http_exc = to_http_exception(exc)
    logger.error(f"LocalDocSearchError: {exc.message}", extra={"details": exc.details})
    return JSONResponse(
        status_code=http_exc.status_code,
        content={"error": exc.message, "details": exc.details},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """予期しないエラーをキャッチ。"""
    logger.exception(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "details": {"message": str(exc)}},
    )


# ルーターを登録
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(actions.router, prefix="/api/actions", tags=["actions"])


@app.get("/health")
async def health():
    """ヘルスチェックエンドポイント。"""
    return {"status": "healthy"}


# 静的ファイルの提供（SvelteKit ビルド）
UI_BUILD_DIR = Path(__file__).parent.parent.parent / "ui" / "build"

if UI_BUILD_DIR.exists():
    # SPAのフォールバック用
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPAを提供。"""
        file_path = UI_BUILD_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        # フォールバックでindex.htmlを返す
        return FileResponse(UI_BUILD_DIR / "index.html")

    # 静的アセットをマウント（_appディレクトリ）
    if (UI_BUILD_DIR / "_app").exists():
        app.mount("/_app", StaticFiles(directory=UI_BUILD_DIR / "_app"), name="static")


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
