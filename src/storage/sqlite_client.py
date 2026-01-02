"""SQLite FTS5クライアント。

BM25全文検索用のSQLiteデータベースへの接続と操作を提供する。
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger()


class SQLiteClient:
    """SQLite FTS5クライアント。"""

    def __init__(self, db_path: Path | None = None):
        """初期化。

        Args:
            db_path: データベースパス（指定しない場合は設定から取得）
        """
        settings = get_settings()
        self.db_path = db_path or settings.sqlite_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """データベース接続を取得。"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """データベースを初期化。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # ドキュメントテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    path TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    extension TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    modified_at TEXT NOT NULL,
                    indexed_at TEXT NOT NULL,
                    is_deleted INTEGER DEFAULT 0,
                    deleted_at TEXT,
                    duration_seconds REAL,
                    width INTEGER,
                    height INTEGER
                )
            """)

            # チャンク用FTS5テーブル
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    chunk_id,
                    document_id,
                    text,
                    path,
                    filename,
                    content='',
                    tokenize='unicode61'
                )
            """)

            # Transcriptテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transcripts (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    full_text TEXT NOT NULL,
                    language TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    word_count INTEGER NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES documents(id)
                )
            """)

            # インデックス
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_path ON documents(path)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(content_hash)"
            )

            logger.info("SQLite database initialized")

    def add_document(self, document: dict[str, Any]) -> None:
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

    def add_chunks_fts(self, chunks: list[dict[str, Any]]) -> None:
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

    def search_fts(
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
                    "bm25_score": abs(row["score"]),  # BM25スコアは負数で返される
                })
            return results

    def get_document_by_id(self, document_id: str) -> dict[str, Any] | None:
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

    def get_document_by_path(self, path: str) -> dict[str, Any] | None:
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

    def get_document_by_hash(self, content_hash: str) -> dict[str, Any] | None:
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

    def delete_document(self, document_id: str, hard_delete: bool = False) -> None:
        """ドキュメントを削除。

        Args:
            document_id: ドキュメントID
            hard_delete: 物理削除するかどうか
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if hard_delete:
                cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
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

    def add_transcript(self, transcript: dict[str, Any]) -> None:
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

    def get_transcript(self, document_id: str) -> dict[str, Any] | None:
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
