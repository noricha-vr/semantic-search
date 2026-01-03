"""動画インデックス処理プロセッサ。"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config.logging import get_logger
from src.indexer.processors.base import BaseMediaProcessor
from src.processors.video_processor import VideoProcessor
from src.storage.models import DocumentRecord
from src.storage.schema import MediaType
from src.storage.sqlite_client import SQLiteClient

logger = get_logger()


class VideoIndexerProcessor(BaseMediaProcessor):
    """動画インデックス処理プロセッサ。

    動画から音声を抽出し、Whisperで文字起こしてインデックス化する。
    """

    def __init__(
        self,
        video_processor: VideoProcessor | None = None,
        sqlite_client: SQLiteClient | None = None,
    ):
        """初期化。

        Args:
            video_processor: 動画プロセッサ（テスト用に差し替え可能）
            sqlite_client: SQLiteクライアント（テスト用に差し替え可能）
        """
        self.video_processor = video_processor or VideoProcessor()
        self.sqlite_client = sqlite_client or SQLiteClient()

    def can_process(self, file_path: Path) -> bool:
        """このプロセッサで処理可能か判定。

        Args:
            file_path: ファイルパス

        Returns:
            処理可能ならTrue
        """
        return self.video_processor.is_supported(file_path)

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

        record = DocumentRecord(
            id=str(uuid.uuid4()),
            content_hash=content_hash,
            path=str(file_path.absolute()),
            filename=file_path.name,
            extension=file_path.suffix.lower(),
            media_type=MediaType.VIDEO.value,
            size=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            indexed_at=now,
        )
        return record.model_dump()

    def process(self, file_path: Path, content_hash: str) -> dict[str, Any] | None:
        """動画をインデックス化。

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

        # 動画処理とインデックス化
        try:
            result = self.video_processor.index_video(file_path, document_id)
            if result:
                transcript = result.get("transcript")
                if transcript:
                    # duration と dimensions を更新
                    doc_record["duration_seconds"] = transcript.get("duration_seconds")
                    doc_record["width"] = result.get("width")
                    doc_record["height"] = result.get("height")
                    self.sqlite_client.add_transcript(transcript)
                logger.info(f"Indexed video: {file_path}, document_id: {document_id}")
                return doc_record
            else:
                # ドキュメントを削除
                self.sqlite_client.delete_document(document_id, hard_delete=True)
                return None
        except Exception as e:
            logger.error(f"Failed to index video {file_path}: {e}")
            self.sqlite_client.delete_document(document_id, hard_delete=True)
            return None
