"""BM25検索。

SQLite FTS5を使用してBM25検索を実行する。
"""

from dataclasses import dataclass

from src.config.logging import get_logger
from src.storage.sqlite_client import SQLiteClient

logger = get_logger()


@dataclass
class BM25Result:
    """BM25検索結果。"""

    chunk_id: str
    document_id: str
    text: str
    path: str
    filename: str
    bm25_score: float


class BM25Search:
    """BM25検索クラス。"""

    def __init__(self):
        """初期化。"""
        self.sqlite_client = SQLiteClient()

    def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[BM25Result]:
        """BM25検索を実行。

        Args:
            query: 検索クエリ
            limit: 結果件数

        Returns:
            検索結果のリスト
        """
        # FTS5用のクエリを作成
        # 複数単語の場合はORで結合
        terms = query.split()
        fts_query = " OR ".join(terms)

        try:
            results = self.sqlite_client.search_fts(fts_query, limit=limit)

            bm25_results = [
                BM25Result(
                    chunk_id=r["chunk_id"],
                    document_id=r["document_id"],
                    text=r["text"],
                    path=r["path"],
                    filename=r["filename"],
                    bm25_score=r["bm25_score"],
                )
                for r in results
            ]

            logger.info(f"BM25 search for '{query}': {len(bm25_results)} results")
            return bm25_results

        except Exception as e:
            logger.error(f"BM25 search error: {e}")
            return []

    def normalize_scores(self, results: list[BM25Result]) -> list[BM25Result]:
        """スコアを正規化（0-1の範囲に）。

        Args:
            results: 検索結果

        Returns:
            正規化された検索結果
        """
        if not results:
            return results

        max_score = max(r.bm25_score for r in results)
        min_score = min(r.bm25_score for r in results)
        score_range = max_score - min_score

        if score_range == 0:
            # すべて同じスコアの場合
            for r in results:
                r.bm25_score = 1.0
        else:
            for r in results:
                r.bm25_score = (r.bm25_score - min_score) / score_range

        return results
