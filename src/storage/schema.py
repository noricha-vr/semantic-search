"""LanceDBスキーマ定義。

ER図（docs/tech/er-diagram.md）に基づいたデータモデルを定義する。
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MediaType(str, Enum):
    """メディアタイプ。"""

    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class Document(BaseModel):
    """ドキュメントモデル。"""

    id: str = Field(..., description="UUID")
    content_hash: str = Field(..., description="SHA-256ハッシュ")
    path: str = Field(..., description="ファイルパス")
    filename: str = Field(..., description="ファイル名")
    extension: str = Field(..., description="拡張子")
    media_type: MediaType = Field(..., description="メディアタイプ")
    size: int = Field(..., description="ファイルサイズ（バイト）")
    created_at: datetime = Field(..., description="ファイル作成日時")
    modified_at: datetime = Field(..., description="ファイル更新日時")
    indexed_at: datetime = Field(..., description="インデックス日時")
    is_deleted: bool = Field(default=False, description="論理削除フラグ")
    deleted_at: datetime | None = Field(default=None, description="削除日時")
    duration_seconds: float | None = Field(default=None, description="動画/音声の長さ")
    width: int | None = Field(default=None, description="画像/動画の幅")
    height: int | None = Field(default=None, description="画像/動画の高さ")


class Chunk(BaseModel):
    """テキストチャンクモデル。"""

    id: str = Field(..., description="UUID")
    document_id: str = Field(..., description="ドキュメントID")
    chunk_index: int = Field(..., description="チャンク番号（0始まり）")
    text: str = Field(..., description="テキスト内容")
    vector: list[float] = Field(..., description="Embedding（1024次元）")
    start_time: float | None = Field(default=None, description="開始時間（秒）")
    end_time: float | None = Field(default=None, description="終了時間（秒）")
    metadata: dict[str, Any] = Field(default_factory=dict, description="追加メタデータ")


class VLMResult(BaseModel):
    """画像のVLM処理結果モデル。"""

    id: str = Field(..., description="UUID")
    document_id: str = Field(..., description="ドキュメントID")
    description: str = Field(..., description="VLMによる説明文")
    ocr_text: str | None = Field(default=None, description="OCR結果")
    vector: list[float] = Field(..., description="Embedding")


class Transcript(BaseModel):
    """動画/音声の文字起こし結果モデル。"""

    id: str = Field(..., description="UUID")
    document_id: str = Field(..., description="ドキュメントID")
    full_text: str = Field(..., description="全文テキスト")
    language: str = Field(..., description="検出言語")
    duration_seconds: float = Field(..., description="長さ（秒）")
    word_count: int = Field(..., description="単語数")


# LanceDB用のテーブルスキーマ
CHUNKS_SCHEMA = {
    "id": "str",
    "document_id": "str",
    "chunk_index": "int",
    "text": "str",
    "vector": "vector[1024]",
    "start_time": "float",
    "end_time": "float",
    "path": "str",
    "filename": "str",
    "media_type": "str",
}

VLM_RESULTS_SCHEMA = {
    "id": "str",
    "document_id": "str",
    "description": "str",
    "ocr_text": "str",
    "vector": "vector[1024]",
    "path": "str",
    "filename": "str",
}
