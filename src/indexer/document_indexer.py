"""ドキュメントインデクサー。

ファイルを処理してインデックス化する。
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config.logging import get_logger
from src.embeddings.ollama_embedding import OllamaEmbeddingClient
from src.indexer.hash_utils import calculate_file_hash
from src.processors.chunker import Chunker
from src.processors.image_processor import ImageProcessor
from src.processors.office_processor import OfficeProcessor
from src.processors.pdf_processor import PDFProcessor
from src.processors.text_processor import TextProcessor
from src.storage.lancedb_client import LanceDBClient
from src.storage.schema import MediaType
from src.storage.sqlite_client import SQLiteClient

logger = get_logger()


class DocumentIndexer:
    """ドキュメントインデクサー。"""

    # 画像拡張子
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".svg"}
    # 動画拡張子
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"}
    # 音声拡張子
    AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".wma"}

    def __init__(self):
        """初期化。"""
        self.pdf_processor = PDFProcessor()
        self.text_processor = TextProcessor()
        self.office_processor = OfficeProcessor()
        self.image_processor = ImageProcessor()
        self.chunker = Chunker()
        self.embedding_client = OllamaEmbeddingClient()
        self.lancedb_client = LanceDBClient()
        self.sqlite_client = SQLiteClient()

    def _get_media_type(self, file_path: Path) -> MediaType:
        """ファイルのメディアタイプを判定。

        Args:
            file_path: ファイルパス

        Returns:
            メディアタイプ
        """
        suffix = file_path.suffix.lower()

        if suffix in self.IMAGE_EXTENSIONS:
            return MediaType.IMAGE
        elif suffix in self.VIDEO_EXTENSIONS:
            return MediaType.VIDEO
        elif suffix in self.AUDIO_EXTENSIONS:
            return MediaType.AUDIO
        else:
            return MediaType.DOCUMENT

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

    def _create_document_record(
        self,
        file_path: Path,
        content_hash: str,
        media_type: MediaType,
    ) -> dict[str, Any]:
        """ドキュメントレコードを作成。

        Args:
            file_path: ファイルパス
            content_hash: コンテンツハッシュ
            media_type: メディアタイプ

        Returns:
            ドキュメントレコード
        """
        stat = file_path.stat()
        now = datetime.now(timezone.utc)

        return {
            "id": str(uuid.uuid4()),
            "content_hash": content_hash,
            "path": str(file_path.absolute()),
            "filename": file_path.name,
            "extension": file_path.suffix.lower(),
            "media_type": media_type.value,
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            "indexed_at": now,
            "is_deleted": False,
            "deleted_at": None,
            "duration_seconds": None,
            "width": None,
            "height": None,
        }

    def index_file(self, file_path: Path | str) -> dict[str, Any] | None:
        """ファイルをインデックス化。

        Args:
            file_path: ファイルパス

        Returns:
            インデックス化されたドキュメント情報またはNone
        """
        file_path = Path(file_path)
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return None

        # ハッシュ計算と重複チェック
        content_hash = calculate_file_hash(file_path)
        existing = self.sqlite_client.get_document_by_hash(content_hash)
        if existing:
            logger.info(f"File already indexed (same hash): {file_path}")
            return existing

        # メディアタイプ判定
        media_type = self._get_media_type(file_path)

        # 画像処理
        if media_type == MediaType.IMAGE:
            return self._index_image(file_path, content_hash)

        # 動画・音声は後のフェーズで対応
        if media_type in (MediaType.VIDEO, MediaType.AUDIO):
            logger.info(f"Skipping media file (not yet supported): {file_path}")
            return None

        # テキスト抽出
        text = self._extract_text(file_path)
        if not text:
            logger.warning(f"No text extracted from: {file_path}")
            return None

        # ドキュメントレコード作成
        doc_record = self._create_document_record(file_path, content_hash, media_type)
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
                "media_type": media_type.value,
            }
            chunk_records.append(chunk_record)
            fts_records.append({
                "id": chunk_id,
                "document_id": document_id,
                "text": chunk.text,
                "path": str(file_path.absolute()),
                "filename": file_path.name,
            })

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

    def index_directory(
        self,
        directory: Path | str,
        recursive: bool = True,
    ) -> list[dict[str, Any]]:
        """ディレクトリ内のファイルをインデックス化。

        Args:
            directory: ディレクトリパス
            recursive: サブディレクトリも処理するか

        Returns:
            インデックス化されたドキュメントのリスト
        """
        directory = Path(directory)
        if not directory.is_dir():
            logger.error(f"Not a directory: {directory}")
            return []

        indexed = []
        pattern = "**/*" if recursive else "*"

        for file_path in directory.glob(pattern):
            if file_path.is_file() and not file_path.name.startswith("."):
                result = self.index_file(file_path)
                if result:
                    indexed.append(result)

        logger.info(f"Indexed {len(indexed)} files from: {directory}")
        return indexed

    def _index_image(
        self,
        file_path: Path,
        content_hash: str,
    ) -> dict[str, Any] | None:
        """画像をインデックス化。

        Args:
            file_path: ファイルパス
            content_hash: コンテンツハッシュ

        Returns:
            ドキュメントレコードまたはNone
        """
        # ドキュメントレコード作成
        doc_record = self._create_document_record(file_path, content_hash, MediaType.IMAGE)
        document_id = doc_record["id"]

        # 画像メタデータを取得して更新
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                doc_record["width"] = img.width
                doc_record["height"] = img.height
        except Exception as e:
            logger.warning(f"Failed to get image metadata: {e}")

        # SQLiteにドキュメントを保存
        self.sqlite_client.add_document(doc_record)

        # 画像処理とインデックス化
        try:
            self.image_processor.index_image(file_path, document_id)
            logger.info(f"Indexed image: {file_path}, document_id: {document_id}")
            return doc_record
        except Exception as e:
            logger.error(f"Failed to index image {file_path}: {e}")
            # ドキュメントを削除
            self.sqlite_client.delete_document(document_id, hard_delete=True)
            return None

    def delete_document(self, document_id: str) -> None:
        """ドキュメントを削除。

        Args:
            document_id: ドキュメントID
        """
        self.lancedb_client.delete_by_document_id(document_id)
        self.sqlite_client.delete_document(document_id)
        logger.info(f"Deleted document: {document_id}")
