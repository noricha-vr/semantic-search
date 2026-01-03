"""画像プロセッサ。

画像ファイルをVLMで処理してインデックス化する。
"""

import uuid
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from src.config.logging import get_logger
from src.embeddings.ollama_embedding import OllamaEmbeddingClient
from src.ocr.vlm_client import VLMClient
from src.processors.image_metadata import (
    ImageMetadataExtractor,
    format_metadata_for_vectorization,
)
from src.storage.lancedb_client import LanceDBClient
from src.storage.sqlite_client import SQLiteClient

logger = get_logger()


@dataclass
class ImageMetadata:
    """画像メタデータ。"""

    width: int
    height: int
    format: str | None
    mode: str


@dataclass
class ImageResult:
    """画像処理結果。"""

    description: str
    ocr_text: str | None
    metadata: ImageMetadata


class ImageProcessor:
    """画像プロセッサ。"""

    SUPPORTED_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".webp",
        ".tiff",
    }

    def __init__(self):
        """初期化。"""
        self.vlm_client = VLMClient()
        self.embedding_client = OllamaEmbeddingClient()
        self.lancedb_client = LanceDBClient()
        self.sqlite_client = SQLiteClient()
        self.metadata_extractor = ImageMetadataExtractor()

    def _get_image_metadata(self, image_path: Path) -> ImageMetadata:
        """画像のメタデータを取得。

        Args:
            image_path: 画像ファイルのパス

        Returns:
            メタデータ
        """
        with Image.open(image_path) as img:
            return ImageMetadata(
                width=img.width,
                height=img.height,
                format=img.format,
                mode=img.mode,
            )

    def process_image(self, image_path: Path | str) -> ImageResult | None:
        """画像を処理。

        Args:
            image_path: 画像ファイルのパス

        Returns:
            処理結果またはNone
        """
        image_path = Path(image_path)
        if not image_path.exists():
            logger.warning(f"Image not found: {image_path}")
            return None

        try:
            # メタデータ取得
            metadata = self._get_image_metadata(image_path)

            # VLMで分析
            analysis = self.vlm_client.analyze_document_image(image_path)

            logger.info(
                f"Processed image: {image_path}, "
                f"size: {metadata.width}x{metadata.height}"
            )

            return ImageResult(
                description=analysis["description"],
                ocr_text=analysis.get("ocr_text"),
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Failed to process image {image_path}: {e}")
            return None

    def index_image(
        self,
        image_path: Path | str,
        document_id: str,
    ) -> dict | None:
        """画像をインデックス化。

        Args:
            image_path: 画像ファイルのパス
            document_id: ドキュメントID

        Returns:
            VLM結果レコードまたはNone
        """
        result = self.process_image(image_path)
        if not result:
            return None

        image_path = Path(image_path)

        # EXIFメタデータを抽出
        exif_metadata = self.metadata_extractor.extract(image_path)
        metadata_text = format_metadata_for_vectorization(exif_metadata)

        # 説明文、OCRテキスト、メタデータを結合してEmbedding生成
        combined_text = result.description
        if result.ocr_text:
            combined_text += f"\n\n{result.ocr_text}"
        if metadata_text:
            combined_text += f"\n\n{metadata_text}"

        embedding = self.embedding_client.embed_text(combined_text)

        # VLM結果レコードを作成
        vlm_result = {
            "id": str(uuid.uuid4()),
            "document_id": document_id,
            "description": result.description,
            "ocr_text": result.ocr_text or "",
            "vector": embedding,
            "path": str(image_path.absolute()),
            "filename": image_path.name,
        }

        # LanceDBに保存
        self.lancedb_client.add_vlm_results([vlm_result])

        # チャンクとしてもFTSに追加（検索可能にするため）
        fts_record = {
            "id": vlm_result["id"],
            "document_id": document_id,
            "text": combined_text,
            "path": str(image_path.absolute()),
            "filename": image_path.name,
        }
        self.sqlite_client.add_chunks_fts([fts_record])

        logger.info(f"Indexed image: {image_path}")
        return vlm_result

    def is_supported(self, file_path: Path | str) -> bool:
        """ファイルがサポートされているかを判定。

        Args:
            file_path: ファイルパス

        Returns:
            サポートされていればTrue
        """
        file_path = Path(file_path)
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS
