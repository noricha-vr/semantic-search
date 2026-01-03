"""チャンクリポジトリ。

チャンク（FTS5）テーブルへの操作を提供する。
"""

from typing import Any

from src.config.logging import get_logger
from src.storage.repositories.base import BaseRepository

logger = get_logger()


class ChunkRepository(BaseRepository):
    """チャンクリポジトリ。"""

    def add_chunks(self, chunks: list[dict[str, Any]]) -> None:
        """チャンクをFTSテーブルに追加。

        Args:
            chunks: チャンクデータのリスト
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for chunk in chunks:
                cursor.execute(
                    """
                    INSERT INTO chunks_fts (chunk_id, document_id, text, path, filename)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        chunk["id"],
                        chunk["document_id"],
                        chunk["text"],
                        chunk["path"],
                        chunk["filename"],
                    ),
                )
            logger.info(f"Added {len(chunks)} chunks to FTS")

    def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """BM25検索を実行。

        Args:
            query: 検索クエリ
            limit: 結果件数

        Returns:
            検索結果のリスト
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    chunk_id,
                    document_id,
                    text,
                    path,
                    filename,
                    bm25(chunks_fts) as score
                FROM chunks_fts
                WHERE chunks_fts MATCH ?
                ORDER BY bm25(chunks_fts)
                LIMIT ?
            """,
                (query, limit),
            )
            results = []
            for row in cursor.fetchall():
                results.append({
                    "chunk_id": row["chunk_id"],
                    "document_id": row["document_id"],
                    "text": row["text"],
                    "path": row["path"],
                    "filename": row["filename"],
                    "bm25_score": abs(row["score"]),
                })
            return results

    def delete_by_document_id(self, document_id: str) -> None:
        """ドキュメントIDに紐づくチャンクを削除。

        Args:
            document_id: ドキュメントID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM chunks_fts WHERE document_id = ?", (document_id,)
            )
            logger.info(f"Deleted chunks for document: {document_id}")
