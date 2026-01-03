"""ドキュメント処理プロセッサ。

PDF、Office、テキストファイルをインデックス化する。
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config.logging import get_logger
from src.config.settings import get_settings
from src.embeddings.ollama_embedding import OllamaEmbeddingClient
from src.indexer.processors.base import BaseMediaProcessor
from src.processors.chunker import Chunker
from src.processors.office_processor import OfficeProcessor
from src.processors.pdf_processor import PDFProcessor
from src.processors.text_processor import TextProcessor
from src.processors.vlm_processor import VLMProcessor
from src.storage.lancedb_client import LanceDBClient
from src.storage.models import DocumentRecord
from src.storage.schema import MediaType
from src.storage.sqlite_client import SQLiteClient

logger = get_logger()


class DocumentProcessor(BaseMediaProcessor):
    """ドキュメント処理プロセッサ。

    PDF、Office、テキストファイルを処理してインデックス化する。
    VLMフォールバックによるPDF画像処理も含む。
    """

    def __init__(
        self,
        pdf_processor: PDFProcessor | None = None,
        text_processor: TextProcessor | None = None,
        office_processor: OfficeProcessor | None = None,
        chunker: Chunker | None = None,
        embedding_client: OllamaEmbeddingClient | None = None,
        lancedb_client: LanceDBClient | None = None,
        sqlite_client: SQLiteClient | None = None,
        vlm_processor: VLMProcessor | None = None,
    ):
        """初期化。

        Args:
            pdf_processor: PDFプロセッサ（テスト用に差し替え可能）
            text_processor: テキストプロセッサ（テスト用に差し替え可能）
            office_processor: Officeプロセッサ（テスト用に差し替え可能）
            chunker: チャンカー（テスト用に差し替え可能）
            embedding_client: 埋め込みクライアント（テスト用に差し替え可能）
            lancedb_client: LanceDBクライアント（テスト用に差し替え可能）
            sqlite_client: SQLiteクライアント（テスト用に差し替え可能）
            vlm_processor: VLMプロセッサ（テスト用に差し替え可能）
        """
        self.settings = get_settings()
        self.pdf_processor = pdf_processor or PDFProcessor()
        self.text_processor = text_processor or TextProcessor()
        self.office_processor = office_processor or OfficeProcessor()
        self.chunker = chunker or Chunker()
        self.embedding_client = embedding_client or OllamaEmbeddingClient()
        self.lancedb_client = lancedb_client or LanceDBClient()
        self.sqlite_client = sqlite_client or SQLiteClient()
        # VLMプロセッサ（遅延初期化）
        self._vlm_processor = vlm_processor

    def _get_vlm_processor(self) -> VLMProcessor:
        """VLMプロセッサを取得（遅延初期化）。"""
        if self._vlm_processor is None:
            self._vlm_processor = VLMProcessor(pdf_processor=self.pdf_processor)
        return self._vlm_processor

    def can_process(self, file_path: Path) -> bool:
        """このプロセッサで処理可能か判定。

        Args:
            file_path: ファイルパス

        Returns:
            処理可能ならTrue
        """
        return (
            self.pdf_processor.is_supported(file_path)
            or self.office_processor.is_supported(file_path)
            or self.text_processor.is_supported(file_path)
        )

    def _create_document_record(
        self,
        file_path: Path,
        content_hash: str,
    ) -> dict[str, Any]:
        """ドキュメントレコードを作成。

        Args:
            file_path: ファイルパス
            content_hash: コンテンツハッシュ

        Returns:
            ドキュメントレコード（後方互換性のためdict形式）
        """
        stat = file_path.stat()
        now = datetime.now(timezone.utc)

        record = DocumentRecord(
            id=str(uuid.uuid4()),
            content_hash=content_hash,
            path=str(file_path.absolute()),
            filename=file_path.name,
            extension=file_path.suffix.lower(),
            media_type=MediaType.DOCUMENT.value,
            size=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            indexed_at=now,
        )
        return record.model_dump()

    def _extract_text(self, file_path: Path) -> str | None:
        """ファイルからテキストを抽出。

        Args:
            file_path: ファイルパス

        Returns:
            抽出されたテキストまたはNone
        """
        try:
            if self.pdf_processor.is_supported(file_path):
                result = self.pdf_processor.extract_text(file_path)
                # VLMフォールバック処理
                if result.pages_needing_vlm and self.settings.pdf_vlm_fallback:
                    vlm_processor = self._get_vlm_processor()
                    return vlm_processor.process_pdf_pages(file_path, result)
                return result.text
            elif self.office_processor.is_supported(file_path):
                result = self.office_processor.extract_text(file_path)
                return result.text
            elif self.text_processor.is_supported(file_path):
                result = self.text_processor.extract_text(file_path)
                return result.text
            else:
                logger.warning(f"Unsupported file type: {file_path}")
                return None
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {e}")
            return None

    def process(self, file_path: Path, content_hash: str) -> dict[str, Any] | None:
        """ドキュメントをインデックス化。

        Args:
            file_path: ファイルパス
            content_hash: コンテンツハッシュ

        Returns:
            ドキュメントレコードまたはNone
        """
        # テキスト抽出
        text = self._extract_text(file_path)
        if not text:
            logger.warning(f"No text extracted from: {file_path}")
            return None

        # ドキュメントレコード作成
        doc_record = self._create_document_record(file_path, content_hash)
        document_id = doc_record["id"]

        # チャンキング
        chunks = self.chunker.chunk_text(text)
        if not chunks:
            logger.warning(f"No chunks created from: {file_path}")
            return None

        # Embedding生成
        chunk_texts = [c.text for c in chunks]
        embeddings = self.embedding_client.embed_batch(chunk_texts)

        # チャンクレコード作成
        chunk_records = []
        fts_records = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = str(uuid.uuid4())
            chunk_record = {
                "id": chunk_id,
                "document_id": document_id,
                "chunk_index": i,
                "text": chunk.text,
                "vector": embedding,
                "start_time": None,
                "end_time": None,
                "path": str(file_path.absolute()),
                "filename": file_path.name,
                "media_type": MediaType.DOCUMENT.value,
            }
            chunk_records.append(chunk_record)
            fts_records.append(
                {
                    "id": chunk_id,
                    "document_id": document_id,
                    "text": chunk.text,
                    "path": str(file_path.absolute()),
                    "filename": file_path.name,
                }
            )

        # データベースに保存
        self.sqlite_client.add_document(doc_record)
        self.lancedb_client.add_chunks(chunk_records)
        self.sqlite_client.add_chunks_fts(fts_records)

        logger.info(
            f"Indexed: {file_path}, "
            f"chunks: {len(chunk_records)}, "
            f"document_id: {document_id}"
        )

        return doc_record

    @property
    def vlm_pages_processed(self) -> int:
        """VLM処理されたページ数を返す。"""
        if self._vlm_processor is None:
            return 0
        return self._vlm_processor.vlm_pages_processed
