"""ハイブリッド検索。

ベクトル検索とBM25検索を組み合わせて検索精度を向上させる。
"""

from dataclasses import dataclass
from typing import Any

from src.config.logging import get_logger
from src.search.bm25_search import BM25Search
from src.search.rrf import RRF, RRFResult
from src.search.vector_search import VectorSearch

logger = get_logger()


@dataclass
class HybridSearchResult:
    """ハイブリッド検索結果。"""

    chunk_id: str
    document_id: str
    text: str
    path: str
    filename: str
    media_type: str
    score: float
    vector_score: float | None
    bm25_score: float | None
    start_time: float | None = None
    end_time: float | None = None


class HybridSearch:
    """ハイブリッド検索クラス。"""

    def __init__(self, rrf_k: int = 60):
        """初期化。

        Args:
            rrf_k: RRFのkパラメータ
        """
        self.vector_search = VectorSearch()
        self.bm25_search = BM25Search()
        self.rrf = RRF(k=rrf_k)

    def search(
        self,
        query: str,
        limit: int = 10,
        vector_weight: float = 0.5,
        bm25_weight: float = 0.5,
        media_types: list[str] | None = None,
        path_prefix: str | None = None,
    ) -> list[HybridSearchResult]:
        """ハイブリッド検索を実行。

        Args:
            query: 検索クエリ
            limit: 結果件数
            vector_weight: ベクトル検索の重み（未使用、RRFを使用）
            bm25_weight: BM25検索の重み（未使用、RRFを使用）
            media_types: フィルターするメディアタイプ
            path_prefix: パスプレフィックスでフィルター

        Returns:
            検索結果のリスト
        """
        # ベクトル検索を実行（多めに取得してRRFで統合）
        fetch_limit = limit * 3
        vector_results = self.vector_search.search(
            query=query,
            limit=fetch_limit,
            media_types=media_types,
            path_prefix=path_prefix,
        )

        # BM25検索を実行
        bm25_results = self.bm25_search.search(query=query, limit=fetch_limit)

        # 結果を辞書形式に変換
        vector_dicts = [
            {
                "chunk_id": r.chunk_id,
                "document_id": r.document_id,
                "text": r.text,
                "path": r.path,
                "filename": r.filename,
                "media_type": r.media_type,
                "score": r.score,
                "start_time": r.start_time,
                "end_time": r.end_time,
            }
            for r in vector_results
        ]

        bm25_dicts = [
            {
                "chunk_id": r.chunk_id,
                "document_id": r.document_id,
                "text": r.text,
                "path": r.path,
                "filename": r.filename,
                "media_type": "document",  # BM25からはメディアタイプが取れないのでデフォルト
                "bm25_score": r.bm25_score,
            }
            for r in bm25_results
        ]

        # RRFで統合
        rrf_results = self.rrf.fuse(vector_dicts, bm25_dicts)

        # 結果を整形
        results = [
            HybridSearchResult(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                text=r.text,
                path=r.path,
                filename=r.filename,
                media_type=r.media_type,
                score=r.rrf_score,
                vector_score=r.vector_score,
                bm25_score=r.bm25_score,
                start_time=r.start_time,
                end_time=r.end_time,
            )
            for r in rrf_results[:limit]
        ]

        logger.info(f"Hybrid search for '{query}': {len(results)} results")
        return results

    def to_dict(self, results: list[HybridSearchResult]) -> list[dict[str, Any]]:
        """検索結果を辞書に変換。

        Args:
            results: 検索結果リスト

        Returns:
            辞書のリスト
        """
        return [
            {
                "chunk_id": r.chunk_id,
                "document_id": r.document_id,
                "text": r.text,
                "path": r.path,
                "filename": r.filename,
                "media_type": r.media_type,
                "score": r.score,
                "vector_score": r.vector_score,
                "bm25_score": r.bm25_score,
                "start_time": r.start_time,
                "end_time": r.end_time,
            }
            for r in results
        ]
