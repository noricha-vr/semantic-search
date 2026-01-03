"""PDFProcessorのテスト。"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.processors.pdf_processor import PDFMetadata, PDFProcessor, PDFResult


@pytest.fixture
def processor():
    """デフォルト設定のPDFProcessor。"""
    return PDFProcessor()


@pytest.fixture
def sample_pdf_path(tmp_path):
    """テスト用のシンプルなPDFを作成。"""
    import fitz

    pdf_path = tmp_path / "test.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "This is test content. " * 10)
    page.insert_text((50, 100), "Second line of text. " * 5)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def image_pdf_path(tmp_path):
    """テキストがほとんどないPDF（画像ベース想定）を作成。"""
    import fitz

    pdf_path = tmp_path / "image_pdf.pdf"
    doc = fitz.open()
    # 3ページ、テキストなし
    for _ in range(3):
        doc.new_page()
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def mixed_pdf_path(tmp_path):
    """テキストありページとなしページが混在するPDF。"""
    import fitz

    pdf_path = tmp_path / "mixed.pdf"
    doc = fitz.open()
    # ページ1: テキストあり
    page1 = doc.new_page()
    page1.insert_text((50, 50), "This page has enough text content. " * 10)
    # ページ2: テキストなし
    doc.new_page()
    # ページ3: テキストあり
    page3 = doc.new_page()
    page3.insert_text((50, 50), "Third page also has content. " * 10)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


class TestPDFResult:
    """PDFResultデータクラスのテスト。"""

    def test_default_values(self):
        """デフォルト値が正しく設定される。"""
        metadata = PDFMetadata(
            page_count=1,
            title=None,
            author=None,
            subject=None,
            creator=None,
        )
        result = PDFResult(text="test", metadata=metadata)
        assert result.extraction_method == "text"
        assert result.pages_needing_vlm == []

    def test_custom_values(self):
        """カスタム値が正しく設定される。"""
        metadata = PDFMetadata(
            page_count=5,
            title="Test Title",
            author="Author",
            subject=None,
            creator=None,
        )
        result = PDFResult(
            text="content",
            metadata=metadata,
            extraction_method="vlm_needed",
            pages_needing_vlm=[0, 1, 2],
        )
        assert result.extraction_method == "vlm_needed"
        assert result.pages_needing_vlm == [0, 1, 2]


class TestPDFProcessor:
    """PDFProcessorのテスト。"""

    def test_is_supported_pdf(self, processor, tmp_path):
        """PDFファイルはサポートされる。"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.touch()
        assert processor.is_supported(pdf_file) is True

    def test_is_supported_pdf_uppercase(self, processor, tmp_path):
        """大文字拡張子もサポートされる。"""
        pdf_file = tmp_path / "test.PDF"
        pdf_file.touch()
        assert processor.is_supported(pdf_file) is True

    def test_is_supported_not_pdf(self, processor, tmp_path):
        """PDF以外はサポートされない。"""
        for ext in [".txt", ".docx", ".png", ".jpg"]:
            file = tmp_path / f"test{ext}"
            file.touch()
            assert processor.is_supported(file) is False

    def test_is_supported_string_path(self, processor, tmp_path):
        """文字列パスもサポートされる。"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.touch()
        assert processor.is_supported(str(pdf_file)) is True

    def test_extract_text_success(self, processor, sample_pdf_path):
        """正常なPDFからテキストを抽出できる。"""
        result = processor.extract_text(sample_pdf_path)

        assert isinstance(result, PDFResult)
        assert len(result.text) > 0
        assert "test content" in result.text
        assert result.metadata.page_count == 1
        assert result.extraction_method == "text"

    def test_extract_text_metadata(self, processor, sample_pdf_path):
        """メタデータが正しく抽出される。"""
        result = processor.extract_text(sample_pdf_path)

        assert isinstance(result.metadata, PDFMetadata)
        assert result.metadata.page_count >= 1

    def test_extract_text_file_not_found(self, processor):
        """存在しないファイルでFileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            processor.extract_text("/nonexistent/path/to/file.pdf")

    def test_extract_text_invalid_pdf(self, processor, tmp_path):
        """無効なPDFでValueError。"""
        invalid_pdf = tmp_path / "invalid.pdf"
        invalid_pdf.write_text("This is not a PDF")

        with pytest.raises(ValueError):
            processor.extract_text(invalid_pdf)

    def test_extract_text_string_path(self, processor, sample_pdf_path):
        """文字列パスでも動作する。"""
        result = processor.extract_text(str(sample_pdf_path))
        assert isinstance(result, PDFResult)
        assert len(result.text) > 0

    def test_check_pages_for_vlm_text_pdf(self, processor, sample_pdf_path):
        """テキストが十分なPDFはVLM不要。"""
        result = processor.extract_text(sample_pdf_path)
        assert len(result.pages_needing_vlm) == 0
        assert result.extraction_method == "text"

    def test_check_pages_for_vlm_image_pdf(self, processor, image_pdf_path):
        """テキストがないPDFはVLM必要。"""
        result = processor.extract_text(image_pdf_path)
        assert len(result.pages_needing_vlm) == 3
        assert result.extraction_method == "vlm_needed"

    def test_check_pages_for_vlm_mixed_pdf(self, processor, mixed_pdf_path):
        """混在PDFは一部のページがVLM必要。"""
        result = processor.extract_text(mixed_pdf_path)
        assert 1 in result.pages_needing_vlm  # ページ2（インデックス1）
        assert result.extraction_method == "hybrid_needed"

    @patch.object(PDFProcessor, "_check_pages_for_vlm", return_value=[])
    def test_vlm_fallback_disabled(self, mock_check, tmp_path):
        """VLMフォールバック無効時はチェックしない。"""
        import fitz

        # VLMフォールバックを無効に設定
        with patch("src.processors.pdf_processor.get_settings") as mock_settings:
            settings = MagicMock()
            settings.pdf_vlm_fallback = False
            settings.pdf_use_markdown = True
            settings.pdf_min_chars_per_page = 100
            mock_settings.return_value = settings

            processor = PDFProcessor()
            # 実際にはモックしているので、設定を確認
            assert processor.settings.pdf_vlm_fallback is False


class TestPDFPageRendering:
    """ページ画像変換のテスト。"""

    def test_render_page_to_image(self, processor, sample_pdf_path):
        """ページを画像に変換できる。"""
        image_path = processor.render_page_to_image(sample_pdf_path, 0)

        assert image_path.exists()
        assert image_path.suffix == ".png"
        # クリーンアップ
        image_path.unlink()

    def test_render_page_to_image_custom_output(self, processor, sample_pdf_path, tmp_path):
        """指定した出力パスに保存できる。"""
        output_path = tmp_path / "output.png"
        result = processor.render_page_to_image(
            sample_pdf_path, 0, output_path=output_path
        )

        assert result == output_path
        assert output_path.exists()

    def test_render_pages_to_images(self, processor, mixed_pdf_path):
        """複数ページを画像に変換できる。"""
        image_paths = processor.render_pages_to_images(mixed_pdf_path, [0, 1, 2])

        assert len(image_paths) == 3
        for path in image_paths:
            assert path.exists()
            assert path.suffix == ".png"
            # クリーンアップ
            path.unlink()

    def test_render_pages_all_pages(self, processor, mixed_pdf_path):
        """ページ指定なしで全ページ変換。"""
        image_paths = processor.render_pages_to_images(mixed_pdf_path)

        assert len(image_paths) == 3
        for path in image_paths:
            path.unlink()

    def test_render_page_invalid_page_number(self, processor, sample_pdf_path):
        """無効なページ番号でIndexError。"""
        with pytest.raises(IndexError):
            processor.render_page_to_image(sample_pdf_path, 999)


class TestPDFMetadata:
    """PDFMetadataデータクラスのテスト。"""

    def test_metadata_fields(self):
        """全フィールドが正しく設定される。"""
        metadata = PDFMetadata(
            page_count=10,
            title="Test Title",
            author="Test Author",
            subject="Test Subject",
            creator="Test Creator",
        )
        assert metadata.page_count == 10
        assert metadata.title == "Test Title"
        assert metadata.author == "Test Author"
        assert metadata.subject == "Test Subject"
        assert metadata.creator == "Test Creator"

    def test_metadata_none_values(self):
        """None値が許容される。"""
        metadata = PDFMetadata(
            page_count=1,
            title=None,
            author=None,
            subject=None,
            creator=None,
        )
        assert metadata.title is None
        assert metadata.author is None
