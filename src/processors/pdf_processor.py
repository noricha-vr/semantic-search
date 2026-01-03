"""PDFテキスト抽出プロセッサ。

PyMuPDF4LLMを使用してPDFからMarkdown形式でテキストを抽出する。
テキストが少ない場合はVLMフォールバックを提供する。
"""

import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF
import pymupdf4llm

from src.config.logging import get_logger
from src.config.settings import get_settings

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
    extraction_method: str = "text"  # "text", "vlm_needed", "hybrid_needed"
    pages_needing_vlm: list[int] = field(default_factory=list)


class PDFProcessor:
    """PDFプロセッサ。"""

    def __init__(self):
        """初期化。"""
        self.settings = get_settings()

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
            # メタデータ抽出
            meta = doc.metadata
            metadata = PDFMetadata(
                page_count=doc.page_count,
                title=meta.get("title") or None,
                author=meta.get("author") or None,
                subject=meta.get("subject") or None,
                creator=meta.get("creator") or None,
            )

            # PyMuPDF4LLMでMarkdown抽出（設定有効時）
            if self.settings.pdf_use_markdown:
                try:
                    full_text = pymupdf4llm.to_markdown(doc)
                except Exception as e:
                    logger.warning(f"PyMuPDF4LLM failed, falling back to basic extraction: {e}")
                    full_text = self._extract_text_basic(doc)
            else:
                full_text = self._extract_text_basic(doc)

            # ページ単位のテキスト量を確認
            pages_needing_vlm = self._check_pages_for_vlm(doc)

            extraction_method = "text"
            if pages_needing_vlm:
                if len(pages_needing_vlm) == doc.page_count:
                    extraction_method = "vlm_needed"
                else:
                    extraction_method = "hybrid_needed"

            logger.info(
                f"Extracted text from PDF: {file_path}, "
                f"pages: {metadata.page_count}, chars: {len(full_text)}, "
                f"method: {extraction_method}, vlm_pages: {len(pages_needing_vlm)}"
            )

            return PDFResult(
                text=full_text,
                metadata=metadata,
                extraction_method=extraction_method,
                pages_needing_vlm=pages_needing_vlm,
            )

        finally:
            doc.close()

    def _extract_text_basic(self, doc: fitz.Document) -> str:
        """基本的なテキスト抽出。

        Args:
            doc: PyMuPDFドキュメント

        Returns:
            抽出されたテキスト
        """
        text_parts = []
        for page in doc:
            text = page.get_text()
            if text.strip():
                text_parts.append(text)
        return "\n\n".join(text_parts)

    def _check_pages_for_vlm(self, doc: fitz.Document) -> list[int]:
        """VLM処理が必要なページを判定。

        Args:
            doc: PyMuPDFドキュメント

        Returns:
            VLM処理が必要なページ番号のリスト（0始まり）
        """
        if not self.settings.pdf_vlm_fallback:
            return []

        min_chars = self.settings.pdf_min_chars_per_page
        pages_needing_vlm = []

        for page_num, page in enumerate(doc):
            text = page.get_text()
            if len(text.strip()) < min_chars:
                pages_needing_vlm.append(page_num)

        return pages_needing_vlm

    def render_page_to_image(
        self,
        file_path: Path | str,
        page_number: int,
        output_path: Path | str | None = None,
    ) -> Path:
        """PDFページを画像に変換。

        Args:
            file_path: PDFファイルのパス
            page_number: ページ番号（0始まり）
            output_path: 出力パス（指定なしで一時ファイル）

        Returns:
            画像ファイルのパス
        """
        file_path = Path(file_path)
        doc = fitz.open(str(file_path))

        try:
            page = doc[page_number]
            pix = page.get_pixmap(dpi=self.settings.pdf_vlm_dpi)

            if output_path is None:
                # 一時ファイルを作成
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                output_path = Path(tmp.name)
                tmp.close()
            else:
                output_path = Path(output_path)

            pix.save(str(output_path))
            logger.debug(f"Rendered PDF page {page_number} to {output_path}")
            return output_path
        finally:
            doc.close()

    def render_pages_to_images(
        self,
        file_path: Path | str,
        page_numbers: list[int] | None = None,
    ) -> list[Path]:
        """複数ページを画像に変換。

        Args:
            file_path: PDFファイルのパス
            page_numbers: ページ番号リスト（Noneで全ページ）

        Returns:
            画像ファイルパスのリスト
        """
        file_path = Path(file_path)
        doc = fitz.open(str(file_path))
        image_paths = []

        try:
            if page_numbers is None:
                page_numbers = list(range(doc.page_count))

            for page_num in page_numbers:
                page = doc[page_num]
                pix = page.get_pixmap(dpi=self.settings.pdf_vlm_dpi)

                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                output_path = Path(tmp.name)
                tmp.close()

                pix.save(str(output_path))
                image_paths.append(output_path)

            logger.debug(f"Rendered {len(image_paths)} PDF pages to images")
            return image_paths
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
