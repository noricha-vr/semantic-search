"""PDFテキスト抽出プロセッサ。

PyMuPDFを使用してPDFからテキストを抽出する。
"""

from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

from src.config.logging import get_logger

logger = get_logger()


@dataclass
class PDFMetadata:
    """PDFメタデータ。"""

    page_count: int
    title: str | None
    author: str | None
    subject: str | None
    creator: str | None


@dataclass
class PDFResult:
    """PDF処理結果。"""

    text: str
    metadata: PDFMetadata


class PDFProcessor:
    """PDFプロセッサ。"""

    def extract_text(self, file_path: Path | str) -> PDFResult:
        """PDFからテキストを抽出。

        Args:
            file_path: PDFファイルのパス

        Returns:
            テキストとメタデータ

        Raises:
            FileNotFoundError: ファイルが見つからない
            ValueError: PDFの読み込みに失敗
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            doc = fitz.open(str(file_path))
        except Exception as e:
            logger.error(f"Failed to open PDF: {file_path}, error: {e}")
            raise ValueError(f"Failed to open PDF: {e}")

        try:
            # テキスト抽出
            text_parts = []
            for page in doc:
                text = page.get_text()
                if text.strip():
                    text_parts.append(text)

            full_text = "\n\n".join(text_parts)

            # メタデータ抽出
            meta = doc.metadata
            metadata = PDFMetadata(
                page_count=doc.page_count,
                title=meta.get("title") or None,
                author=meta.get("author") or None,
                subject=meta.get("subject") or None,
                creator=meta.get("creator") or None,
            )

            logger.info(
                f"Extracted text from PDF: {file_path}, "
                f"pages: {metadata.page_count}, chars: {len(full_text)}"
            )

            return PDFResult(text=full_text, metadata=metadata)

        finally:
            doc.close()

    def is_supported(self, file_path: Path | str) -> bool:
        """ファイルがPDFかどうかを判定。

        Args:
            file_path: ファイルパス

        Returns:
            PDFならTrue
        """
        file_path = Path(file_path)
        return file_path.suffix.lower() == ".pdf"
