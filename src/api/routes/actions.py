"""アクションAPIルート。

ファイル操作アクションを提供するエンドポイント。
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.api.file_opener import FileOpener
from src.config.logging import get_logger
from src.storage.sqlite_client import SQLiteClient

logger = get_logger()
router = APIRouter()


class OpenFileRequest(BaseModel):
    """ファイルを開くリクエスト。"""

    path: str = Field(..., description="ファイルパス")
    start_time: float | None = Field(default=None, description="開始時間（秒）")


class OpenFileResponse(BaseModel):
    """ファイルを開くレスポンス。"""

    success: bool
    path: str
    start_time: float | None = None


class RevealRequest(BaseModel):
    """Finderで表示リクエスト。"""

    path: str = Field(..., description="ファイルパス")


class RevealResponse(BaseModel):
    """Finderで表示レスポンス。"""

    success: bool
    path: str


@router.post("/open", response_model=OpenFileResponse)
async def open_file(request: OpenFileRequest):
    """ファイルを開く。

    音声・動画ファイルの場合、start_timeを指定すると該当位置から再生する。
    """
    path = Path(request.path)

    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    opener = FileOpener()
    success = opener.open_file(path, start_time=request.start_time)

    return OpenFileResponse(
        success=success,
        path=str(path),
        start_time=request.start_time,
    )


@router.post("/reveal", response_model=RevealResponse)
async def reveal_in_finder(request: RevealRequest):
    """Finderでファイルの場所を表示。"""
    path = Path(request.path)

    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    opener = FileOpener()
    success = opener.reveal_in_finder(path)

    return RevealResponse(
        success=success,
        path=str(path),
    )


@router.post("/open-by-document/{document_id}", response_model=OpenFileResponse)
async def open_by_document_id(
    document_id: str,
    start_time: float | None = None,
):
    """ドキュメントIDでファイルを開く。"""
    client = SQLiteClient()
    doc = client.get_document_by_id(document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    path = Path(doc["path"])

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="File no longer exists at the indexed path",
        )

    opener = FileOpener()
    success = opener.open_file(path, start_time=start_time)

    return OpenFileResponse(
        success=success,
        path=str(path),
        start_time=start_time,
    )


@router.post("/reveal-by-document/{document_id}", response_model=RevealResponse)
async def reveal_by_document_id(document_id: str):
    """ドキュメントIDでFinderに表示。"""
    client = SQLiteClient()
    doc = client.get_document_by_id(document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    path = Path(doc["path"])

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="File no longer exists at the indexed path",
        )

    opener = FileOpener()
    success = opener.reveal_in_finder(path)

    return RevealResponse(
        success=success,
        path=str(path),
    )
