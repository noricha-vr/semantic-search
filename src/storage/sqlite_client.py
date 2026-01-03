"""SQLite FTS5クライアント。

BM25全文検索用のSQLiteデータベースへの接続と操作を提供する。
リポジトリパターンを使用して責務を分割。
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from src.config.logging import get_logger
from src.config.settings import get_settings
from src.storage.repositories import (
    ChunkRepository,
    DocumentRepository,
    TranscriptRepository,
)

logger = get_logger()


class SQLiteClient:
    """SQLite FTS5クライアント。

    後方互換性を維持しつつ、リポジトリに処理を委譲する。
    """

    def __init__(self, db_path: Path | None = None):
        """初期化。

        Args:
            db_path: データベースパス（指定しない場合は設定から取得）
        """
        settings = get_settings()
        self.db_path = db_path or settings.sqlite_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # リポジトリの初期化
        self._document_repo = DocumentRepository(self.db_path)
        self._chunk_repo = ChunkRepository(self.db_path)
        self._transcript_repo = TranscriptRepository(self.db_path)

        self._init_db()

    @property
    def documents(self) -> DocumentRepository:
        """ドキュメントリポジトリを取得。"""
        return self._document_repo

    @property
    def chunks(self) -> ChunkRepository:
        """チャンクリポジトリを取得。"""
        return self._chunk_repo

    @property
    def transcripts(self) -> TranscriptRepository:
        """トランスクリプトリポジトリを取得。"""
        return self._transcript_repo

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

            # チャンク用FTS5テーブル（コンテンツを保持する標準FTS5）
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    chunk_id,
                    document_id,
                    text,
                    path,
                    filename,
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

    # 後方互換性のためのメソッド（リポジトリに委譲）

    def add_document(self, document: dict[str, Any]) -> None:
        """ドキュメントを追加。

        Args:
            document: ドキュメントデータ
        """
        self._document_repo.add(document)

    def add_chunks_fts(self, chunks: list[dict[str, Any]]) -> None:
        """チャンクをFTSテーブルに追加。

        Args:
            chunks: チャンクデータのリスト
        """
        self._chunk_repo.add_chunks(chunks)

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
        return self._chunk_repo.search(query, limit)

    def get_document_by_id(self, document_id: str) -> dict[str, Any] | None:
        """IDでドキュメントを取得。

        Args:
            document_id: ドキュメントID

        Returns:
            ドキュメントデータまたはNone
        """
        return self._document_repo.get_by_id(document_id)

    def get_document_by_path(self, path: str) -> dict[str, Any] | None:
        """パスでドキュメントを取得。

        Args:
            path: ファイルパス

        Returns:
            ドキュメントデータまたはNone
        """
        return self._document_repo.get_by_path(path)

    def get_document_by_hash(self, content_hash: str) -> dict[str, Any] | None:
        """ハッシュでドキュメントを取得。

        Args:
            content_hash: コンテンツハッシュ

        Returns:
            ドキュメントデータまたはNone
        """
        return self._document_repo.get_by_hash(content_hash)

    def delete_document(self, document_id: str, hard_delete: bool = False) -> None:
        """ドキュメントを削除。

        Args:
            document_id: ドキュメントID
            hard_delete: 物理削除するかどうか
        """
        self._document_repo.delete(document_id, hard_delete, delete_related=True)

    def add_transcript(self, transcript: dict[str, Any]) -> None:
        """Transcriptを追加。

        Args:
            transcript: Transcriptデータ
        """
        self._transcript_repo.add(transcript)

    def get_transcript(self, document_id: str) -> dict[str, Any] | None:
        """ドキュメントIDでTranscriptを取得。

        Args:
            document_id: ドキュメントID

        Returns:
            Transcriptデータまたはなし
        """
        return self._transcript_repo.get_by_document_id(document_id)

    def get_stats(self) -> dict[str, Any]:
        """統計情報を取得。

        Returns:
            統計情報の辞書
        """
        return self._document_repo.get_stats()

    def get_indexed_directories(self) -> list[dict[str, Any]]:
        """インデックス済みディレクトリを取得。

        Returns:
            ディレクトリパスとファイル数のリスト
        """
        return self._document_repo.get_indexed_directories()

    def get_recent_documents(
        self, limit: int = 10, media_type: str | None = None
    ) -> list[dict[str, Any]]:
        """最近インデックスされたドキュメントを取得。

        Args:
            limit: 取得件数
            media_type: メディアタイプでフィルタ

        Returns:
            ドキュメントのリスト
        """
        return self._document_repo.get_recent(limit, media_type)
