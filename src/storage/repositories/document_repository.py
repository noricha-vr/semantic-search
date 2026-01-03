"""ドキュメントリポジトリ。

ドキュメントテーブルへのCRUD操作を提供する。
"""

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config.logging import get_logger
from src.storage.repositories.base import BaseRepository

logger = get_logger()


class DocumentRepository(BaseRepository):
    """ドキュメントリポジトリ。"""

    def add(self, document: dict[str, Any]) -> None:
        """ドキュメントを追加。

        Args:
            document: ドキュメントデータ
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO documents
                (id, content_hash, path, filename, extension, media_type, size,
                 created_at, modified_at, indexed_at, is_deleted, deleted_at,
                 duration_seconds, width, height)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    document["id"],
                    document["content_hash"],
                    document["path"],
                    document["filename"],
                    document["extension"],
                    document["media_type"],
                    document["size"],
                    document["created_at"].isoformat()
                    if isinstance(document["created_at"], datetime)
                    else document["created_at"],
                    document["modified_at"].isoformat()
                    if isinstance(document["modified_at"], datetime)
                    else document["modified_at"],
                    document["indexed_at"].isoformat()
                    if isinstance(document["indexed_at"], datetime)
                    else document["indexed_at"],
                    1 if document.get("is_deleted", False) else 0,
                    document.get("deleted_at"),
                    document.get("duration_seconds"),
                    document.get("width"),
                    document.get("height"),
                ),
            )
            logger.info(f"Added document: {document['path']}")

    def get_by_id(self, document_id: str) -> dict[str, Any] | None:
        """IDでドキュメントを取得。

        Args:
            document_id: ドキュメントID

        Returns:
            ドキュメントデータまたはNone
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_by_path(self, path: str) -> dict[str, Any] | None:
        """パスでドキュメントを取得。

        Args:
            path: ファイルパス

        Returns:
            ドキュメントデータまたはNone
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE path = ?", (path,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_by_hash(self, content_hash: str) -> dict[str, Any] | None:
        """ハッシュでドキュメントを取得。

        Args:
            content_hash: コンテンツハッシュ

        Returns:
            ドキュメントデータまたはNone
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM documents WHERE content_hash = ?", (content_hash,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def delete(
        self,
        document_id: str,
        hard_delete: bool = False,
        delete_related: bool = True,
    ) -> None:
        """ドキュメントを削除。

        Args:
            document_id: ドキュメントID
            hard_delete: 物理削除するかどうか
            delete_related: 関連データ（チャンク、トランスクリプト）も削除するか
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if hard_delete:
                cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
                if delete_related:
                    cursor.execute(
                        "DELETE FROM chunks_fts WHERE document_id = ?", (document_id,)
                    )
                    cursor.execute(
                        "DELETE FROM transcripts WHERE document_id = ?", (document_id,)
                    )
            else:
                cursor.execute(
                    """
                    UPDATE documents
                    SET is_deleted = 1, deleted_at = ?
                    WHERE id = ?
                """,
                    (datetime.now().isoformat(), document_id),
                )
            logger.info(f"Deleted document: {document_id}")

    def get_stats(self) -> dict[str, Any]:
        """統計情報を取得。

        Returns:
            統計情報の辞書
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT COUNT(*) as total FROM documents WHERE is_deleted = 0"
            )
            total = cursor.fetchone()["total"]

            cursor.execute("""
                SELECT media_type, COUNT(*) as count
                FROM documents
                WHERE is_deleted = 0
                GROUP BY media_type
            """)
            by_type = {row["media_type"]: row["count"] for row in cursor.fetchall()}

            cursor.execute("SELECT COUNT(*) as total FROM chunks_fts")
            total_chunks = cursor.fetchone()["total"]

            cursor.execute(
                "SELECT MAX(indexed_at) as last FROM documents WHERE is_deleted = 0"
            )
            last_indexed = cursor.fetchone()["last"]

            return {
                "total_documents": total,
                "by_media_type": by_type,
                "total_chunks": total_chunks,
                "last_indexed_at": last_indexed,
            }

    def get_indexed_directories(self) -> list[dict[str, Any]]:
        """インデックス済みディレクトリを取得。

        Returns:
            ディレクトリパスとファイル数のリスト
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT path FROM documents WHERE is_deleted = 0
            """)
            paths = [row["path"] for row in cursor.fetchall()]

        dir_counts: Counter[str] = Counter()
        for path in paths:
            p = Path(path)
            if len(p.parts) >= 3:
                base = str(Path(*p.parts[:4]))
            else:
                base = str(p.parent)
            dir_counts[base] += 1

        return [
            {"path": path, "file_count": count}
            for path, count in dir_counts.most_common(20)
        ]

    def get_recent(
        self, limit: int = 10, media_type: str | None = None
    ) -> list[dict[str, Any]]:
        """最近インデックスされたドキュメントを取得。

        Args:
            limit: 取得件数
            media_type: メディアタイプでフィルタ

        Returns:
            ドキュメントのリスト
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if media_type:
                cursor.execute(
                    """
                    SELECT * FROM documents
                    WHERE is_deleted = 0 AND media_type = ?
                    ORDER BY indexed_at DESC
                    LIMIT ?
                """,
                    (media_type, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM documents
                    WHERE is_deleted = 0
                    ORDER BY indexed_at DESC
                    LIMIT ?
                """,
                    (limit,),
                )
            return [dict(row) for row in cursor.fetchall()]
