"""音声インデックス処理プロセッサ。"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config.logging import get_logger
from src.indexer.processors.base import BaseMediaProcessor
from src.processors.audio_processor import AudioProcessor
from src.storage.models import DocumentRecord
from src.storage.schema import MediaType
from src.storage.sqlite_client import SQLiteClient

logger = get_logger()


class AudioIndexerProcessor(BaseMediaProcessor):
    """音声インデックス処理プロセッサ。

    Whisperを使用して音声を文字起こしし、インデックス化する。
    """

    def __init__(
        self,
        audio_processor: AudioProcessor | None = None,
        sqlite_client: SQLiteClient | None = None,
    ):
        """初期化。

        Args:
            audio_processor: 音声プロセッサ（テスト用に差し替え可能）
            sqlite_client: SQLiteクライアント（テスト用に差し替え可能）
        """
        self.audio_processor = audio_processor or AudioProcessor()
        self.sqlite_client = sqlite_client or SQLiteClient()

    def can_process(self, file_path: Path) -> bool:
        """このプロセッサで処理可能か判定。

        Args:
            file_path: ファイルパス

        Returns:
            処理可能ならTrue
        """
        return self.audio_processor.is_supported(file_path)

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
            media_type=MediaType.AUDIO.value,
            size=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            indexed_at=now,
        )
        return record.model_dump()

    def process(self, file_path: Path, content_hash: str) -> dict[str, Any] | None:
        """音声をインデックス化。

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

        # 音声処理とインデックス化
        try:
            transcript = self.audio_processor.index_audio(file_path, document_id)
            if transcript:
                # duration を更新
                doc_record["duration_seconds"] = transcript.get("duration_seconds")
                self.sqlite_client.add_transcript(transcript)
                logger.info(f"Indexed audio: {file_path}, document_id: {document_id}")
                return doc_record
            else:
                # ドキュメントを削除
                self.sqlite_client.delete_document(document_id, hard_delete=True)
                return None
        except Exception as e:
            logger.error(f"Failed to index audio {file_path}: {e}")
            self.sqlite_client.delete_document(document_id, hard_delete=True)
            return None
