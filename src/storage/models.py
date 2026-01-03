"""Pydantic models for storage layer.

データベースレコードの型安全なモデルを定義。
"""

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentRecord(BaseModel):
    """ドキュメントレコード。

    ドキュメントテーブルの1行を表す。
    """

    id: str
    content_hash: str
    path: str
    filename: str
    extension: str
    media_type: str
    size: int
    created_at: datetime
    modified_at: datetime
    indexed_at: datetime
    is_deleted: bool = False
    deleted_at: datetime | None = None
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None


class ChunkRecord(BaseModel):
    """チャンクレコード。

    FTSテーブルに保存されるチャンク情報。
    """

    id: str
    document_id: str
    text: str
    path: str
    filename: str


class TranscriptRecord(BaseModel):
    """トランスクリプトレコード。

    音声・動画のトランスクリプト情報。
    """

    id: str
    document_id: str
    full_text: str
    language: str
    duration_seconds: float
    word_count: int


class DocumentStats(BaseModel):
    """統計情報。

    インデックスの統計サマリー。
    """

    total_documents: int
    by_media_type: dict[str, int]
    total_chunks: int
    last_indexed_at: str | None = None


class IndexedDirectory(BaseModel):
    """インデックス済みディレクトリ。"""

    path: str
    file_count: int


class SearchChunkResult(BaseModel):
    """BM25検索結果のチャンク。"""

    chunk_id: str
    document_id: str
    text: str
    path: str
    filename: str
    bm25_score: float = Field(ge=0)
