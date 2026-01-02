"""ドキュメントAPIルート。

ドキュメント管理機能を提供するエンドポイント。
"""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.indexer.document_indexer import DocumentIndexer
from src.storage.sqlite_client import SQLiteClient

logger = get_logger()
router = APIRouter()


class DocumentResponse(BaseModel):
    """ドキュメントレスポンス。"""

    id: str
    path: str
    filename: str
    extension: str
    media_type: str
    size: int
    created_at: str
    modified_at: str
    indexed_at: str
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None


class DocumentListResponse(BaseModel):
    """ドキュメントリストレスポンス。"""

    total: int
    documents: list[DocumentResponse]


class IndexRequest(BaseModel):
    """インデックスリクエスト。"""

    path: str = Field(..., description="インデックス対象のパス")
    recursive: bool = Field(default=True, description="サブディレクトリも処理するか")


class IndexResponse(BaseModel):
    """インデックスレスポンス。"""

    indexed_count: int
    paths: list[str]


class StatsResponse(BaseModel):
    """統計レスポンス。"""

    total_documents: int
    by_media_type: dict[str, int]
    total_chunks: int
    last_indexed_at: str | None


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    limit: int = Query(default=50, ge=1, le=500, description="取得件数"),
    offset: int = Query(default=0, ge=0, description="オフセット"),
    media_type: str | None = Query(default=None, description="メディアタイプフィルタ"),
):
    """ドキュメント一覧を取得。"""
    client = SQLiteClient()

    # TODO: 実際のページネーションクエリに置き換え
    stats = client.get_stats()

    return DocumentListResponse(
        total=stats["total_documents"],
        documents=[],  # TODO: 実際のドキュメントリストを返す
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """統計情報を取得。"""
    client = SQLiteClient()
    stats = client.get_stats()

    return StatsResponse(
        total_documents=stats["total_documents"],
        by_media_type=stats["by_media_type"],
        total_chunks=stats["total_chunks"],
        last_indexed_at=stats["last_indexed_at"],
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    """ドキュメント詳細を取得。"""
    client = SQLiteClient()
    doc = client.get_document_by_id(document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        id=doc["id"],
        path=doc["path"],
        filename=doc["filename"],
        extension=doc["extension"],
        media_type=doc["media_type"],
        size=doc["size"],
        created_at=doc["created_at"],
        modified_at=doc["modified_at"],
        indexed_at=doc["indexed_at"],
        duration_seconds=doc.get("duration_seconds"),
        width=doc.get("width"),
        height=doc.get("height"),
    )


@router.post("/index", response_model=IndexResponse)
async def index_path(request: IndexRequest):
    """パスをインデックス化。"""
    path = Path(request.path).expanduser()

    if not path.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    indexer = DocumentIndexer()
    indexed_paths = []

    if path.is_file():
        result = indexer.index_file(path)
        if result:
            indexed_paths.append(str(path))
    else:
        results = indexer.index_directory(path, recursive=request.recursive)
        indexed_paths = [r["path"] for r in results]

    return IndexResponse(
        indexed_count=len(indexed_paths),
        paths=indexed_paths,
    )


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """ドキュメントを削除。"""
    client = SQLiteClient()
    doc = client.get_document_by_id(document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    indexer = DocumentIndexer()
    indexer.delete_document(document_id)

    return {"status": "deleted", "document_id": document_id}


class TranscriptResponse(BaseModel):
    """Transcriptレスポンス。"""

    id: str
    document_id: str
    full_text: str
    language: str
    duration_seconds: float
    word_count: int


@router.get("/{document_id}/transcript", response_model=TranscriptResponse | None)
async def get_transcript(document_id: str):
    """ドキュメントのTranscriptを取得。"""
    client = SQLiteClient()
    doc = client.get_document_by_id(document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    transcript = client.get_transcript(document_id)
    if not transcript:
        return None

    return TranscriptResponse(
        id=transcript["id"],
        document_id=transcript["document_id"],
        full_text=transcript["full_text"],
        language=transcript["language"],
        duration_seconds=transcript["duration_seconds"],
        word_count=transcript["word_count"],
    )
