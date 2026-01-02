"""リランカー。

検索結果をリランキングして精度を向上させる。
"""

from dataclasses import dataclass
from typing import Any

import ollama

from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger()


@dataclass
class RerankedResult:
    """リランキング結果。"""

    chunk_id: str
    document_id: str
    text: str
    path: str
    filename: str
    media_type: str
    original_score: float
    rerank_score: float
    final_score: float
    start_time: float | None = None
    end_time: float | None = None


class Reranker:
    """リランカー。"""

    def __init__(self, model: str | None = None):
        """初期化。

        Args:
            model: モデル名
        """
        settings = get_settings()
        self.model = model or settings.reranker_model
        self.host = settings.ollama_host
        self._client = ollama.Client(host=self.host)
        self._model_available: bool | None = None

    def _check_model_available(self) -> bool:
        """リランカーモデルが利用可能かチェック。"""
        if self._model_available is not None:
            return self._model_available

        try:
            models = self._client.list()
            available = any(
                self.model.split(":")[0] in m.get("name", "")
                for m in models.get("models", [])
            )
            self._model_available = available
            return available
        except Exception:
            self._model_available = False
            return False

    def _score_with_embedding(
        self,
        query: str,
        text: str,
    ) -> float:
        """Embeddingを使用してスコアを計算。

        リランカーモデルが利用できない場合のフォールバック。
        BGE-M3のEmbeddingでコサイン類似度を計算。

        Args:
            query: クエリ
            text: テキスト

        Returns:
            スコア（0-1）
        """
        try:
            from src.embeddings.ollama_embedding import OllamaEmbeddingClient

            client = OllamaEmbeddingClient()
            query_vec = client.embed_text(query)
            text_vec = client.embed_text(text)
            similarity = client.similarity(query_vec, text_vec)
            # -1〜1を0〜1に正規化
            return (similarity + 1) / 2
        except Exception as e:
            logger.warning(f"Fallback scoring failed: {e}")
            return 0.5

    def rerank(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int | None = None,
        original_weight: float = 0.3,
        rerank_weight: float = 0.7,
    ) -> list[RerankedResult]:
        """検索結果をリランキング。

        Args:
            query: 検索クエリ
            results: 検索結果のリスト
            top_k: 返す件数（Noneの場合は全件）
            original_weight: 元のスコアの重み
            rerank_weight: リランクスコアの重み

        Returns:
            リランキングされた結果
        """
        if not results:
            return []

        # モデルが利用可能かチェック
        use_model = self._check_model_available()

        reranked = []
        for r in results:
            text = r.get("text", "")
            original_score = r.get("score", 0.0)

            if use_model:
                # リランカーモデルを使用（将来の実装）
                # 現在はEmbeddingフォールバックを使用
                rerank_score = self._score_with_embedding(query, text)
            else:
                # Embeddingでスコアリング
                rerank_score = self._score_with_embedding(query, text)

            final_score = (
                original_weight * original_score + rerank_weight * rerank_score
            )

            reranked.append(
                RerankedResult(
                    chunk_id=r.get("chunk_id", ""),
                    document_id=r.get("document_id", ""),
                    text=text,
                    path=r.get("path", ""),
                    filename=r.get("filename", ""),
                    media_type=r.get("media_type", "document"),
                    original_score=original_score,
                    rerank_score=rerank_score,
                    final_score=final_score,
                    start_time=r.get("start_time"),
                    end_time=r.get("end_time"),
                )
            )

        # 最終スコアでソート
        reranked.sort(key=lambda x: x.final_score, reverse=True)

        if top_k:
            reranked = reranked[:top_k]

        logger.info(f"Reranked {len(reranked)} results")
        return reranked

    def to_dict(self, results: list[RerankedResult]) -> list[dict[str, Any]]:
        """結果を辞書に変換。

        Args:
            results: リランキング結果

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
                "score": r.final_score,
                "original_score": r.original_score,
                "rerank_score": r.rerank_score,
                "start_time": r.start_time,
                "end_time": r.end_time,
            }
            for r in results
        ]
