"""ドキュメントインデクサー。

ファイルを処理してインデックス化する。
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config.logging import get_logger
from src.config.settings import get_settings
from src.constants.media_types import get_media_type
from src.embeddings.ollama_embedding import OllamaEmbeddingClient
from src.indexer.hash_utils import calculate_file_hash
from src.indexer.processors.audio_indexer import AudioIndexerProcessor
from src.indexer.processors.document_processor import DocumentProcessor
from src.indexer.processors.image_indexer import ImageIndexerProcessor
from src.indexer.processors.video_indexer import VideoIndexerProcessor
from src.processors.audio_processor import AudioProcessor
from src.processors.chunker import Chunker
from src.processors.image_processor import ImageProcessor
from src.processors.office_processor import OfficeProcessor
from src.processors.pdf_processor import PDFProcessor
from src.processors.text_processor import TextProcessor
from src.processors.video_processor import VideoProcessor
from src.storage.lancedb_client import LanceDBClient
from src.storage.models import DocumentRecord
from src.storage.schema import MediaType
from src.storage.sqlite_client import SQLiteClient

logger = get_logger()


class DocumentIndexer:
    """ドキュメントインデクサー。"""

    def __init__(self):
        """初期化。"""
        self.settings = get_settings()
        self.pdf_processor = PDFProcessor()
        self.text_processor = TextProcessor()
        self.office_processor = OfficeProcessor()
        self.image_processor = ImageProcessor()
        self.audio_processor = AudioProcessor()
        self.video_processor = VideoProcessor()
        self.chunker = Chunker()
        self.embedding_client = OllamaEmbeddingClient()
        self.lancedb_client = LanceDBClient()
        self.sqlite_client = SQLiteClient()

        # メディアタイプ別プロセッサを初期化（依存関係を注入）
        self._image_indexer = ImageIndexerProcessor(
            image_processor=self.image_processor,
            sqlite_client=self.sqlite_client,
        )
        self._audio_indexer = AudioIndexerProcessor(
            audio_processor=self.audio_processor,
            sqlite_client=self.sqlite_client,
        )
        self._video_indexer = VideoIndexerProcessor(
            video_processor=self.video_processor,
            sqlite_client=self.sqlite_client,
        )
        self._document_indexer = DocumentProcessor(
            pdf_processor=self.pdf_processor,
            text_processor=self.text_processor,
            office_processor=self.office_processor,
            chunker=self.chunker,
            embedding_client=self.embedding_client,
            lancedb_client=self.lancedb_client,
            sqlite_client=self.sqlite_client,
        )

    def _get_media_type(self, file_path: Path) -> MediaType:
        """ファイルのメディアタイプを判定。

        Args:
            file_path: ファイルパス

        Returns:
            メディアタイプ
        """
        return get_media_type(file_path)

    def _extract_text(self, file_path: Path) -> str | None:
        """ファイルからテキストを抽出。

        後方互換性のために残しているが、DocumentProcessorを使用することを推奨。

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
            media_type=media_type.value,
            size=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            indexed_at=now,
        )
        return record.model_dump()

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

        # 画像処理（プロセッサに委譲）
        if media_type == MediaType.IMAGE:
            return self._image_indexer.process(file_path, content_hash)

        # 音声処理（プロセッサに委譲）
        if media_type == MediaType.AUDIO:
            return self._audio_indexer.process(file_path, content_hash)

        # 動画処理（プロセッサに委譲）
        if media_type == MediaType.VIDEO:
            return self._video_indexer.process(file_path, content_hash)

        # ドキュメント処理（プロセッサに委譲）
        return self._document_indexer.process(file_path, content_hash)

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

        後方互換性のために残しているが、内部ではプロセッサに委譲。

        Args:
            file_path: ファイルパス
            content_hash: コンテンツハッシュ

        Returns:
            ドキュメントレコードまたはNone
        """
        return self._image_indexer.process(file_path, content_hash)

    def _index_audio(
        self,
        file_path: Path,
        content_hash: str,
    ) -> dict[str, Any] | None:
        """音声をインデックス化。

        後方互換性のために残しているが、内部ではプロセッサに委譲。

        Args:
            file_path: ファイルパス
            content_hash: コンテンツハッシュ

        Returns:
            ドキュメントレコードまたはNone
        """
        return self._audio_indexer.process(file_path, content_hash)

    def _index_video(
        self,
        file_path: Path,
        content_hash: str,
    ) -> dict[str, Any] | None:
        """動画をインデックス化。

        後方互換性のために残しているが、内部ではプロセッサに委譲。

        Args:
            file_path: ファイルパス
            content_hash: コンテンツハッシュ

        Returns:
            ドキュメントレコードまたはNone
        """
        return self._video_indexer.process(file_path, content_hash)

    def delete_document(self, document_id: str) -> None:
        """ドキュメントを削除。

        Args:
            document_id: ドキュメントID
        """
        self.lancedb_client.delete_by_document_id(document_id)
        self.sqlite_client.delete_document(document_id)
        logger.info(f"Deleted document: {document_id}")
