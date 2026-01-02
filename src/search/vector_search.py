"""ベクトル検索。

LanceDBを使用してベクトル検索を実行する。
"""

from dataclasses import dataclass
from typing import Any

from src.config.logging import get_logger
from src.embeddings.ollama_embedding import OllamaEmbeddingClient
from src.storage.lancedb_client import LanceDBClient

logger = get_logger()


@dataclass
class SearchResult:
    """検索結果。"""

    chunk_id: str
    document_id: str
    text: str
    path: str
    filename: str
    media_type: str
    score: float
    start_time: float | None = None
    end_time: float | None = None


class VectorSearch:
    """ベクトル検索クラス。"""

    def __init__(self):
        """初期化。"""
        self.embedding_client = OllamaEmbeddingClient()
        self.lancedb_client = LanceDBClient()

    def search(
        self,
        query: str,
        limit: int = 10,
        media_types: list[str] | None = None,
        path_prefix: str | None = None,
    ) -> list[SearchResult]:
        """ベクトル検索を実行。

        Args:
            query: 検索クエリ
            limit: 結果件数
            media_types: フィルターするメディアタイプ
            path_prefix: パスプレフィックスでフィルター

        Returns:
            検索結果のリスト
        """
        # クエリをEmbedding化
        query_vector = self.embedding_client.embed_text(query)

        # フィルター式を構築
        filter_expr = None
        filters = []

        if media_types:
            media_filter = " OR ".join([f'media_type = "{mt}"' for mt in media_types])
            filters.append(f"({media_filter})")

        if path_prefix:
            filters.append(f'path LIKE "{path_prefix}%"')

        if filters:
            filter_expr = " AND ".join(filters)

        # チャンク検索
        chunk_results = self.lancedb_client.search_chunks(
            query_vector=query_vector,
            limit=limit,
            filter_expr=filter_expr,
        )

        # VLM結果も検索
        vlm_results = []
        if not media_types or "image" in media_types:
            vlm_results = self.lancedb_client.search_vlm_results(
                query_vector=query_vector,
                limit=limit,
            )

        # 結果を統合
        results = []
        for r in chunk_results:
            results.append(
                SearchResult(
                    chunk_id=r["id"],
                    document_id=r["document_id"],
                    text=r["text"],
                    path=r["path"],
                    filename=r["filename"],
                    media_type=r["media_type"],
                    score=1.0 - r.get("_distance", 0),  # 距離をスコアに変換
                    start_time=r.get("start_time"),
                    end_time=r.get("end_time"),
                )
            )

        # VLM結果を追加（画像）
        for r in vlm_results:
            # descriptionとocr_textを結合してテキストとして使用
            text_parts = []
            if r.get("description"):
                text_parts.append(r["description"])
            if r.get("ocr_text"):
                text_parts.append(f"[OCR] {r['ocr_text']}")
            text = "\n".join(text_parts) if text_parts else "No description"

            results.append(
                SearchResult(
                    chunk_id=r["id"],
                    document_id=r["document_id"],
                    text=text,
                    path=r["path"],
                    filename=r["filename"],
                    media_type="image",
                    score=1.0 - r.get("_distance", 0),
                )
            )

        # スコアでソート
        results.sort(key=lambda x: x.score, reverse=True)

        logger.info(f"Vector search for '{query}': {len(results)} results")
        return results

    def search_similar(
        self,
        document_id: str,
        limit: int = 10,
    ) -> list[SearchResult]:
        """類似ドキュメントを検索。

        Args:
            document_id: 基準となるドキュメントID
            limit: 結果件数

        Returns:
            検索結果のリスト
        """
        # 指定ドキュメントのチャンクを取得
        table = self.lancedb_client.get_or_create_chunks_table()
        chunks = table.search().where(f'document_id = "{document_id}"').limit(1).to_list()

        if not chunks:
            logger.warning(f"Document not found: {document_id}")
            return []

        # 最初のチャンクのベクトルで検索
        query_vector = chunks[0]["vector"]
        results = self.lancedb_client.search_chunks(
            query_vector=query_vector,
            limit=limit + 1,  # 自分自身を除くために1つ多く取得
            filter_expr=f'document_id != "{document_id}"',
        )

        return [
            SearchResult(
                chunk_id=r["id"],
                document_id=r["document_id"],
                text=r["text"],
                path=r["path"],
                filename=r["filename"],
                media_type=r["media_type"],
                score=1.0 - r.get("_distance", 0),
                start_time=r.get("start_time"),
                end_time=r.get("end_time"),
            )
            for r in results[:limit]
        ]

    def to_dict(self, results: list[SearchResult]) -> list[dict[str, Any]]:
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
                "start_time": r.start_time,
                "end_time": r.end_time,
            }
            for r in results
        ]
