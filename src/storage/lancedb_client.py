"""LanceDB接続クライアント。

ベクトルデータベースへの接続とCRUD操作を提供する。
"""

from pathlib import Path
from typing import Any

import lancedb
import numpy as np
from lancedb.table import Table

from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger()


class LanceDBClient:
    """LanceDBクライアント。"""

    CHUNKS_TABLE = "chunks"
    VLM_RESULTS_TABLE = "vlm_results"

    def __init__(self, db_path: Path | None = None):
        """初期化。

        Args:
            db_path: データベースパス（指定しない場合は設定から取得）
        """
        settings = get_settings()
        self.db_path = db_path or settings.lancedb_path
        self.db_path.mkdir(parents=True, exist_ok=True)
        self._db: lancedb.DBConnection | None = None

    @property
    def db(self) -> lancedb.DBConnection:
        """データベース接続を取得。"""
        if self._db is None:
            self._db = lancedb.connect(str(self.db_path))
        return self._db

    def _create_chunks_table(self) -> Table:
        """チャンクテーブルを作成。"""
        import pyarrow as pa

        schema = pa.schema([
            pa.field("id", pa.string()),
            pa.field("document_id", pa.string()),
            pa.field("chunk_index", pa.int32()),
            pa.field("text", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), 1024)),
            pa.field("start_time", pa.float32()),
            pa.field("end_time", pa.float32()),
            pa.field("path", pa.string()),
            pa.field("filename", pa.string()),
            pa.field("media_type", pa.string()),
        ])
        return self.db.create_table(self.CHUNKS_TABLE, schema=schema)

    def _create_vlm_results_table(self) -> Table:
        """VLM結果テーブルを作成。"""
        import pyarrow as pa

        schema = pa.schema([
            pa.field("id", pa.string()),
            pa.field("document_id", pa.string()),
            pa.field("description", pa.string()),
            pa.field("ocr_text", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), 1024)),
            pa.field("path", pa.string()),
            pa.field("filename", pa.string()),
        ])
        return self.db.create_table(self.VLM_RESULTS_TABLE, schema=schema)

    def get_or_create_chunks_table(self) -> Table:
        """チャンクテーブルを取得または作成。"""
        if self.CHUNKS_TABLE in self.db.table_names():
            return self.db.open_table(self.CHUNKS_TABLE)
        return self._create_chunks_table()

    def get_or_create_vlm_results_table(self) -> Table:
        """VLM結果テーブルを取得または作成。"""
        if self.VLM_RESULTS_TABLE in self.db.table_names():
            return self.db.open_table(self.VLM_RESULTS_TABLE)
        return self._create_vlm_results_table()

    def add_chunks(self, chunks: list[dict[str, Any]]) -> None:
        """チャンクを追加。

        Args:
            chunks: チャンクデータのリスト
        """
        table = self.get_or_create_chunks_table()
        table.add(chunks)
        logger.info(f"Added {len(chunks)} chunks to LanceDB")

    def add_vlm_results(self, results: list[dict[str, Any]]) -> None:
        """VLM結果を追加。

        Args:
            results: VLM結果データのリスト
        """
        table = self.get_or_create_vlm_results_table()
        table.add(results)
        logger.info(f"Added {len(results)} VLM results to LanceDB")

    def search_chunks(
        self,
        query_vector: list[float] | np.ndarray,
        limit: int = 10,
        filter_expr: str | None = None,
    ) -> list[dict[str, Any]]:
        """チャンクをベクトル検索。

        Args:
            query_vector: クエリベクトル
            limit: 結果件数
            filter_expr: フィルター式

        Returns:
            検索結果のリスト
        """
        table = self.get_or_create_chunks_table()
        query = table.search(query_vector).limit(limit)
        if filter_expr:
            query = query.where(filter_expr)
        return query.to_list()

    def search_vlm_results(
        self,
        query_vector: list[float] | np.ndarray,
        limit: int = 10,
        filter_expr: str | None = None,
    ) -> list[dict[str, Any]]:
        """VLM結果をベクトル検索。

        Args:
            query_vector: クエリベクトル
            limit: 結果件数
            filter_expr: フィルター式

        Returns:
            検索結果のリスト
        """
        table = self.get_or_create_vlm_results_table()
        query = table.search(query_vector).limit(limit)
        if filter_expr:
            query = query.where(filter_expr)
        return query.to_list()

    def delete_by_document_id(self, document_id: str) -> None:
        """ドキュメントIDでデータを削除。

        Args:
            document_id: ドキュメントID
        """
        chunks_table = self.get_or_create_chunks_table()
        chunks_table.delete(f'document_id = "{document_id}"')

        vlm_table = self.get_or_create_vlm_results_table()
        vlm_table.delete(f'document_id = "{document_id}"')

        logger.info(f"Deleted data for document_id: {document_id}")

    def get_table_stats(self) -> dict[str, int]:
        """テーブルの統計情報を取得。

        Returns:
            テーブル名と行数の辞書
        """
        stats = {}
        for table_name in self.db.table_names():
            table = self.db.open_table(table_name)
            stats[table_name] = len(table)
        return stats
