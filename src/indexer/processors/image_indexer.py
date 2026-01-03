"""画像インデックス処理プロセッサ。"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

from src.config.logging import get_logger
from src.indexer.processors.base import BaseMediaProcessor
from src.processors.image_processor import ImageProcessor
from src.storage.models import DocumentRecord
from src.storage.schema import MediaType
from src.storage.sqlite_client import SQLiteClient

logger = get_logger()


class ImageIndexerProcessor(BaseMediaProcessor):
    """画像インデックス処理プロセッサ。

    VLMを使用して画像を分析し、インデックス化する。
    """

    def __init__(
        self,
        image_processor: ImageProcessor | None = None,
        sqlite_client: SQLiteClient | None = None,
    ):
        """初期化。

        Args:
            image_processor: 画像プロセッサ（テスト用に差し替え可能）
            sqlite_client: SQLiteクライアント（テスト用に差し替え可能）
        """
        self.image_processor = image_processor or ImageProcessor()
        self.sqlite_client = sqlite_client or SQLiteClient()

    def can_process(self, file_path: Path) -> bool:
        """このプロセッサで処理可能か判定。

        Args:
            file_path: ファイルパス

        Returns:
            処理可能ならTrue
        """
        return self.image_processor.is_supported(file_path)

    def _create_document_record(
        self,
        file_path: Path,
        content_hash: str,
    ) -> dict[str, Any]:
        """ドキュメントレコードを作成。

        Args:
            file_path: ファイルパス
            content_hash: コンテンツハッシュ

        Returns:
            ドキュメントレコード（後方互換性のためdict形式）
        """
        stat = file_path.stat()
        now = datetime.now(timezone.utc)

        # 画像メタデータを取得
        width = None
        height = None
        try:
            with Image.open(file_path) as img:
                width = img.width
                height = img.height
        except Exception as e:
            logger.warning(f"Failed to get image metadata: {e}")

        record = DocumentRecord(
            id=str(uuid.uuid4()),
            content_hash=content_hash,
            path=str(file_path.absolute()),
            filename=file_path.name,
            extension=file_path.suffix.lower(),
            media_type=MediaType.IMAGE.value,
            size=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            indexed_at=now,
            width=width,
            height=height,
        )
        return record.model_dump()

    def process(self, file_path: Path, content_hash: str) -> dict[str, Any] | None:
        """画像をインデックス化。

        Args:
            file_path: ファイルパス
            content_hash: コンテンツハッシュ

        Returns:
            ドキュメントレコードまたはNone
        """
        # ドキュメントレコード作成
        doc_record = self._create_document_record(file_path, content_hash)
        document_id = doc_record["id"]

        # SQLiteにドキュメントを保存
        self.sqlite_client.add_document(doc_record)

        # 画像処理とインデックス化
        try:
            self.image_processor.index_image(file_path, document_id)
            logger.info(f"Indexed image: {file_path}, document_id: {document_id}")
            return doc_record
        except Exception as e:
            logger.error(f"Failed to index image {file_path}: {e}")
            # ドキュメントを削除
            self.sqlite_client.delete_document(document_id, hard_delete=True)
            return None
