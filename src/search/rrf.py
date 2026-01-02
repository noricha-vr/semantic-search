"""Reciprocal Rank Fusion (RRF)。

複数の検索結果を統合するアルゴリズム。
"""

from dataclasses import dataclass
from typing import Any

from src.config.logging import get_logger

logger = get_logger()


@dataclass
class RRFResult:
    """RRF統合結果。"""

    chunk_id: str
    document_id: str
    text: str
    path: str
    filename: str
    media_type: str
    rrf_score: float
    vector_score: float | None = None
    bm25_score: float | None = None
    vector_rank: int | None = None
    bm25_rank: int | None = None
    start_time: float | None = None
    end_time: float | None = None


class RRF:
    """Reciprocal Rank Fusion。"""

    def __init__(self, k: int = 60):
        """初期化。

        Args:
            k: RRFのパラメータ（デフォルト60）
        """
        self.k = k

    def fuse(
        self,
        vector_results: list[dict[str, Any]],
        bm25_results: list[dict[str, Any]],
    ) -> list[RRFResult]:
        """複数の検索結果を統合。

        Args:
            vector_results: ベクトル検索結果
            bm25_results: BM25検索結果

        Returns:
            統合された検索結果
        """
        # chunk_idをキーにした辞書を作成
        combined: dict[str, dict[str, Any]] = {}

        # ベクトル検索結果を処理
        for rank, r in enumerate(vector_results, 1):
            chunk_id = r.get("chunk_id") or r.get("id")
            if chunk_id not in combined:
                combined[chunk_id] = {
                    "chunk_id": chunk_id,
                    "document_id": r.get("document_id"),
                    "text": r.get("text"),
                    "path": r.get("path"),
                    "filename": r.get("filename"),
                    "media_type": r.get("media_type", "document"),
                    "start_time": r.get("start_time"),
                    "end_time": r.get("end_time"),
                    "vector_score": r.get("score"),
                    "vector_rank": rank,
                    "bm25_score": None,
                    "bm25_rank": None,
                }
            else:
                combined[chunk_id]["vector_score"] = r.get("score")
                combined[chunk_id]["vector_rank"] = rank

        # BM25検索結果を処理
        for rank, r in enumerate(bm25_results, 1):
            chunk_id = r.get("chunk_id") or r.get("id")
            if chunk_id not in combined:
                combined[chunk_id] = {
                    "chunk_id": chunk_id,
                    "document_id": r.get("document_id"),
                    "text": r.get("text"),
                    "path": r.get("path"),
                    "filename": r.get("filename"),
                    "media_type": r.get("media_type", "document"),
                    "start_time": None,
                    "end_time": None,
                    "vector_score": None,
                    "vector_rank": None,
                    "bm25_score": r.get("bm25_score"),
                    "bm25_rank": rank,
                }
            else:
                combined[chunk_id]["bm25_score"] = r.get("bm25_score")
                combined[chunk_id]["bm25_rank"] = rank

        # RRFスコアを計算
        results = []
        for chunk_id, data in combined.items():
            rrf_score = 0.0

            if data["vector_rank"] is not None:
                rrf_score += 1.0 / (self.k + data["vector_rank"])

            if data["bm25_rank"] is not None:
                rrf_score += 1.0 / (self.k + data["bm25_rank"])

            results.append(
                RRFResult(
                    chunk_id=data["chunk_id"],
                    document_id=data["document_id"],
                    text=data["text"],
                    path=data["path"],
                    filename=data["filename"],
                    media_type=data["media_type"],
                    rrf_score=rrf_score,
                    vector_score=data["vector_score"],
                    bm25_score=data["bm25_score"],
                    vector_rank=data["vector_rank"],
                    bm25_rank=data["bm25_rank"],
                    start_time=data["start_time"],
                    end_time=data["end_time"],
                )
            )

        # RRFスコアでソート
        results.sort(key=lambda x: x.rrf_score, reverse=True)

        logger.info(
            f"RRF fusion: {len(vector_results)} vector + {len(bm25_results)} BM25 "
            f"-> {len(results)} combined"
        )

        return results
