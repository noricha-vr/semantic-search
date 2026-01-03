"""トランスクリプトリポジトリ。

トランスクリプトテーブルへの操作を提供する。
"""

from typing import Any

from src.config.logging import get_logger
from src.storage.repositories.base import BaseRepository

logger = get_logger()


class TranscriptRepository(BaseRepository):
    """トランスクリプトリポジトリ。"""

    def add(self, transcript: dict[str, Any]) -> None:
        """Transcriptを追加。

        Args:
            transcript: Transcriptデータ
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO transcripts
                (id, document_id, full_text, language, duration_seconds, word_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    transcript["id"],
                    transcript["document_id"],
                    transcript["full_text"],
                    transcript["language"],
                    transcript["duration_seconds"],
                    transcript["word_count"],
                ),
            )
            logger.info(f"Added transcript for document: {transcript['document_id']}")

    def get_by_document_id(self, document_id: str) -> dict[str, Any] | None:
        """ドキュメントIDでTranscriptを取得。

        Args:
            document_id: ドキュメントID

        Returns:
            Transcriptデータまたはなし
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM transcripts WHERE document_id = ?", (document_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def delete_by_document_id(self, document_id: str) -> None:
        """ドキュメントIDに紐づくトランスクリプトを削除。

        Args:
            document_id: ドキュメントID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM transcripts WHERE document_id = ?", (document_id,)
            )
            logger.info(f"Deleted transcript for document: {document_id}")
