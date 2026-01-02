"""Ollama Embeddingクライアント。

BGE-M3を使用してテキストをEmbeddingに変換する。
"""

import ollama
import numpy as np

from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger()


class OllamaEmbeddingClient:
    """Ollama Embeddingクライアント。"""

    EMBEDDING_DIM = 1024

    def __init__(self, model: str | None = None):
        """初期化。

        Args:
            model: モデル名（指定しない場合は設定から取得）
        """
        settings = get_settings()
        self.model = model or settings.embedding_model
        self.host = settings.ollama_host
        self._client = ollama.Client(host=self.host)

    def embed_text(self, text: str) -> list[float]:
        """テキストをEmbeddingに変換。

        Args:
            text: テキスト

        Returns:
            1024次元のEmbeddingベクトル
        """
        try:
            response = self._client.embed(model=self.model, input=text)
            embedding = response["embeddings"][0]
            return embedding
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            raise

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """複数テキストをバッチでEmbeddingに変換。

        Args:
            texts: テキストのリスト

        Returns:
            Embeddingベクトルのリスト
        """
        try:
            response = self._client.embed(model=self.model, input=texts)
            return response["embeddings"]
        except Exception as e:
            logger.error(f"Batch embedding error: {e}")
            raise

    def embed_text_numpy(self, text: str) -> np.ndarray:
        """テキストをnumpy配列のEmbeddingに変換。

        Args:
            text: テキスト

        Returns:
            1024次元のnumpy配列
        """
        embedding = self.embed_text(text)
        return np.array(embedding, dtype=np.float32)

    def embed_batch_numpy(self, texts: list[str]) -> np.ndarray:
        """複数テキストをnumpy配列のEmbeddingに変換。

        Args:
            texts: テキストのリスト

        Returns:
            (N, 1024)のnumpy配列
        """
        embeddings = self.embed_batch(texts)
        return np.array(embeddings, dtype=np.float32)

    def similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """コサイン類似度を計算。

        Args:
            vec1: ベクトル1
            vec2: ベクトル2

        Returns:
            コサイン類似度（-1〜1）
        """
        a = np.array(vec1)
        b = np.array(vec2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
