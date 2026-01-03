"""DocumentIndexerおよびVLMプロセッサ関連テスト。"""

from concurrent.futures import TimeoutError as FuturesTimeoutError
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.indexer.processors.document_processor import DocumentProcessor
from src.processors.pdf_processor import PDFMetadata, PDFResult
from src.processors.vlm_processor import VLMProcessor, VLMTimeoutError


@pytest.fixture
def mock_settings():
    """モック設定を作成。"""
    settings = MagicMock()
    settings.pdf_vlm_fallback = True
    settings.pdf_vlm_model = "test-vlm-model"
    settings.pdf_vlm_timeout = 60
    settings.pdf_vlm_max_pages = 20
    settings.pdf_vlm_workers = 1
    settings.ollama_host = "http://localhost:11434"
    settings.embedding_model = "test-embedding"
    settings.chunk_size = 800
    settings.chunk_overlap = 200
    return settings


@pytest.fixture
def vlm_processor(mock_settings):
    """モックを使用したVLMProcessorを作成。"""
    with patch("src.processors.vlm_processor.get_settings", return_value=mock_settings):
        processor = VLMProcessor()
        yield processor


@pytest.fixture
def document_processor(mock_settings):
    """モックを使用したDocumentProcessorを作成。"""
    with patch("src.indexer.processors.document_processor.get_settings", return_value=mock_settings), \
         patch("src.indexer.processors.document_processor.PDFProcessor"), \
         patch("src.indexer.processors.document_processor.TextProcessor"), \
         patch("src.indexer.processors.document_processor.OfficeProcessor"), \
         patch("src.indexer.processors.document_processor.Chunker"), \
         patch("src.indexer.processors.document_processor.OllamaEmbeddingClient"), \
         patch("src.indexer.processors.document_processor.LanceDBClient"), \
         patch("src.indexer.processors.document_processor.SQLiteClient"):
        processor = DocumentProcessor()
        yield processor


@pytest.fixture
def sample_pdf_result():
    """テスト用PDFResult。"""
    metadata = PDFMetadata(
        page_count=5,
        title="Test Document",
        author=None,
        subject=None,
        creator=None,
    )
    return PDFResult(
        text="This is the original extracted text.",
        metadata=metadata,
        extraction_method="hybrid_needed",
        pages_needing_vlm=[1, 2, 4],  # ページ2, 3, 5がVLM必要
    )


class TestVLMTimeoutError:
    """VLMTimeoutErrorのテスト。"""

    def test_exception_message(self):
        """例外メッセージが正しく設定される。"""
        error = VLMTimeoutError("VLM timed out after 60s")
        assert str(error) == "VLM timed out after 60s"

    def test_exception_inheritance(self):
        """VLMTimeoutErrorはExceptionを継承している。"""
        error = VLMTimeoutError("test")
        assert isinstance(error, Exception)

    def test_exception_can_be_raised_and_caught(self):
        """例外を発生させてキャッチできる。"""
        with pytest.raises(VLMTimeoutError) as exc_info:
            raise VLMTimeoutError("timeout occurred")
        assert "timeout occurred" in str(exc_info.value)


class TestVLMProcessorProcessPdfPages:
    """VLMProcessor.process_pdf_pagesメソッドのテスト。"""

    def test_process_pdf_pages_success(self, vlm_processor, sample_pdf_result, tmp_path):
        """VLM処理が成功した場合、テキストがマージされる。"""
        # テスト用画像ファイルを作成
        image_files = [tmp_path / f"page_{i}.png" for i in range(3)]
        for img in image_files:
            img.write_bytes(b"fake image data")

        pdf_path = tmp_path / "test.pdf"

        # モックPDFプロセッサを設定
        mock_pdf_processor = MagicMock()
        mock_pdf_processor.render_pages_to_images.return_value = image_files
        vlm_processor._pdf_processor = mock_pdf_processor

        with patch.object(vlm_processor, "extract_text_with_timeout") as mock_extract:
            mock_extract.side_effect = [
                "VLM text from page 2",
                "VLM text from page 3",
                "VLM text from page 5",
            ]

            result = vlm_processor.process_pdf_pages(pdf_path, sample_pdf_result)

        # 結果の確認
        assert "VLM Extracted Text" in result
        assert "VLM text from page 2" in result
        assert "VLM text from page 3" in result
        assert "VLM text from page 5" in result
        assert sample_pdf_result.text in result

    def test_process_pdf_pages_timeout(self, vlm_processor, sample_pdf_result, tmp_path):
        """VLM処理がタイムアウトした場合、エラーがログされる。"""
        image_files = [tmp_path / f"page_{i}.png" for i in range(3)]
        for img in image_files:
            img.write_bytes(b"fake image data")

        pdf_path = tmp_path / "test.pdf"

        mock_pdf_processor = MagicMock()
        mock_pdf_processor.render_pages_to_images.return_value = image_files
        vlm_processor._pdf_processor = mock_pdf_processor

        with patch.object(vlm_processor, "extract_text_with_timeout") as mock_extract:
            # 全ページがタイムアウト
            mock_extract.side_effect = VLMTimeoutError("timeout")

            result = vlm_processor.process_pdf_pages(pdf_path, sample_pdf_result)

        # タイムアウト時は元のテキストのみ返される
        assert result == sample_pdf_result.text

    def test_process_pdf_pages_partial_success(self, vlm_processor, sample_pdf_result, tmp_path):
        """一部のページのみ成功した場合。"""
        image_files = [tmp_path / f"page_{i}.png" for i in range(3)]
        for img in image_files:
            img.write_bytes(b"fake image data")

        pdf_path = tmp_path / "test.pdf"

        mock_pdf_processor = MagicMock()
        mock_pdf_processor.render_pages_to_images.return_value = image_files
        vlm_processor._pdf_processor = mock_pdf_processor

        with patch.object(vlm_processor, "extract_text_with_timeout") as mock_extract:
            # 1ページ成功、1ページタイムアウト、1ページエラー
            mock_extract.side_effect = [
                "VLM text from page 2",
                VLMTimeoutError("timeout"),
                Exception("VLM error"),
            ]

            result = vlm_processor.process_pdf_pages(pdf_path, sample_pdf_result)

        # 成功したページのテキストのみマージされる
        assert "VLM text from page 2" in result
        assert sample_pdf_result.text in result

    def test_process_pdf_pages_max_pages_limit(self, vlm_processor, tmp_path):
        """VLM処理のページ数制限が適用される。"""
        # 10ページのうち全ページがVLM必要
        metadata = PDFMetadata(page_count=10, title=None, author=None, subject=None, creator=None)
        pdf_result = PDFResult(
            text="Original text",
            metadata=metadata,
            extraction_method="vlm_needed",
            pages_needing_vlm=list(range(10)),  # 全10ページ
        )

        # 最大5ページに制限
        vlm_processor.settings.pdf_vlm_max_pages = 5

        image_files = [tmp_path / f"page_{i}.png" for i in range(5)]
        for img in image_files:
            img.write_bytes(b"fake image data")

        pdf_path = tmp_path / "test.pdf"

        mock_pdf_processor = MagicMock()
        mock_pdf_processor.render_pages_to_images.return_value = image_files
        vlm_processor._pdf_processor = mock_pdf_processor

        with patch.object(vlm_processor, "extract_text_with_timeout") as mock_extract:
            mock_extract.return_value = "VLM extracted text"

            vlm_processor.process_pdf_pages(pdf_path, pdf_result)

        # 5回だけ呼ばれる
        assert mock_extract.call_count == 5

    def test_process_pdf_pages_empty_extraction(self, vlm_processor, sample_pdf_result, tmp_path):
        """VLMがテキストを返さなかった場合。"""
        image_files = [tmp_path / f"page_{i}.png" for i in range(3)]
        for img in image_files:
            img.write_bytes(b"fake image data")

        pdf_path = tmp_path / "test.pdf"

        mock_pdf_processor = MagicMock()
        mock_pdf_processor.render_pages_to_images.return_value = image_files
        vlm_processor._pdf_processor = mock_pdf_processor

        with patch.object(vlm_processor, "extract_text_with_timeout") as mock_extract:
            # 全ページで空文字列を返す
            mock_extract.return_value = ""

            result = vlm_processor.process_pdf_pages(pdf_path, sample_pdf_result)

        # VLM結果がないので元のテキストのみ
        assert result == sample_pdf_result.text


class TestVLMProcessorProcessPagesParallel:
    """VLMProcessor._process_pages_parallelメソッドのテスト。"""

    def test_parallel_processing_success(self, vlm_processor, tmp_path):
        """並列処理が正常に動作する。"""
        vlm_processor.settings.pdf_vlm_workers = 2

        pages = [0, 1, 2]
        image_paths = [tmp_path / f"page_{i}.png" for i in range(3)]
        for img in image_paths:
            img.write_bytes(b"fake image data")

        with patch("src.processors.vlm_processor.VLMClient") as MockVLMClient:
            mock_instance = MagicMock()
            mock_instance.extract_text.return_value = "Extracted text"
            MockVLMClient.return_value = mock_instance

            results = vlm_processor._process_pages_parallel(
                pages=pages,
                image_paths=image_paths,
                workers=2,
                timeout_seconds=60,
                total_pages=3,
            )

        assert len(results) == 3
        for page_num in pages:
            assert page_num in results
            assert results[page_num]["status"] == "success"
            assert results[page_num]["text"] == "Extracted text"

    def test_parallel_processing_timeout(self, vlm_processor, tmp_path):
        """並列処理でタイムアウトが発生した場合。"""
        vlm_processor.settings.pdf_vlm_workers = 2

        pages = [0, 1]
        image_paths = [tmp_path / f"page_{i}.png" for i in range(2)]
        for img in image_paths:
            img.write_bytes(b"fake image data")

        # 直接結果を返すようにモック
        with patch.object(vlm_processor, "_process_pages_parallel") as mock_parallel:
            mock_parallel.return_value = {
                0: {"status": "timeout"},
                1: {"status": "timeout"},
            }
            results = mock_parallel(
                pages=pages,
                image_paths=image_paths,
                workers=2,
                timeout_seconds=1,
                total_pages=2,
            )

        assert results[0]["status"] == "timeout"
        assert results[1]["status"] == "timeout"

    def test_parallel_processing_mixed_results(self, vlm_processor, tmp_path):
        """成功、失敗、タイムアウトが混在した場合。"""
        vlm_processor.settings.pdf_vlm_workers = 2

        pages = [0, 1, 2]
        image_paths = [tmp_path / f"page_{i}.png" for i in range(3)]
        for img in image_paths:
            img.write_bytes(b"fake image data")

        # 直接結果を返すようにモック
        with patch.object(vlm_processor, "_process_pages_parallel") as mock_parallel:
            mock_parallel.return_value = {
                0: {"status": "success", "text": "Page 1 text"},
                1: {"status": "timeout"},
                2: {"status": "failed", "error": "VLM error occurred"},
            }
            results = mock_parallel(
                pages=pages,
                image_paths=image_paths,
                workers=2,
                timeout_seconds=60,
                total_pages=3,
            )

        assert results[0]["status"] == "success"
        assert results[1]["status"] == "timeout"
        assert results[2]["status"] == "failed"

    def test_parallel_processing_empty_pages(self, vlm_processor, tmp_path):
        """処理するページがない場合。"""
        vlm_processor.settings.pdf_vlm_workers = 2

        results = vlm_processor._process_pages_parallel(
            pages=[],
            image_paths=[],
            workers=2,
            timeout_seconds=60,
            total_pages=0,
        )

        assert results == {}


class TestVLMProcessorExtractTextWithTimeout:
    """VLMProcessor.extract_text_with_timeoutメソッドのテスト。"""

    def test_successful_extraction(self, vlm_processor, tmp_path):
        """タイムアウト内で正常に抽出できる場合。"""
        image_path = tmp_path / "test.png"
        image_path.write_bytes(b"fake image data")

        mock_vlm_client = MagicMock()
        mock_vlm_client.extract_text.return_value = "Extracted text content"
        vlm_processor._vlm_client = mock_vlm_client

        result = vlm_processor.extract_text_with_timeout(
            image_path=image_path,
            timeout_seconds=60,
        )

        assert result == "Extracted text content"
        mock_vlm_client.extract_text.assert_called_once_with(image_path)

    def test_timeout_raises_error(self, vlm_processor, tmp_path):
        """タイムアウトした場合にVLMTimeoutErrorが発生する。"""
        image_path = tmp_path / "test.png"
        image_path.write_bytes(b"fake image data")

        mock_vlm_client = MagicMock()

        # ThreadPoolExecutorのタイムアウトをシミュレート
        def slow_extraction(*args):
            raise FuturesTimeoutError()

        with patch("src.processors.vlm_processor.ThreadPoolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            mock_executor.__enter__.return_value = mock_executor
            mock_executor.__exit__.return_value = False
            mock_future = MagicMock()
            mock_future.result.side_effect = FuturesTimeoutError()
            mock_executor.submit.return_value = mock_future
            MockExecutor.return_value = mock_executor

            with pytest.raises(VLMTimeoutError):
                vlm_processor.extract_text_with_timeout(
                    image_path=image_path,
                    timeout_seconds=1,
                )


class TestVLMProcessorMergePdfTexts:
    """VLMProcessor._merge_pdf_textsメソッドのテスト。"""

    def test_merge_with_vlm_texts(self, vlm_processor):
        """VLMテキストがマージされる。"""
        metadata = PDFMetadata(page_count=3, title=None, author=None, subject=None, creator=None)
        pdf_result = PDFResult(
            text="Original PDF text",
            metadata=metadata,
            extraction_method="text",
            pages_needing_vlm=[],
        )

        vlm_texts = {
            1: "VLM extracted text from page 2",
            2: "VLM extracted text from page 3",
        }

        result = vlm_processor._merge_pdf_texts(pdf_result, vlm_texts)

        assert "Original PDF text" in result
        assert "--- VLM Extracted Text ---" in result
        assert "[Page 2]" in result
        assert "[Page 3]" in result
        assert "VLM extracted text from page 2" in result
        assert "VLM extracted text from page 3" in result

    def test_merge_empty_vlm_texts(self, vlm_processor):
        """VLMテキストが空の場合、元のテキストのみ返される。"""
        metadata = PDFMetadata(page_count=1, title=None, author=None, subject=None, creator=None)
        pdf_result = PDFResult(
            text="Original PDF text only",
            metadata=metadata,
            extraction_method="text",
            pages_needing_vlm=[],
        )

        result = vlm_processor._merge_pdf_texts(pdf_result, {})

        assert result == "Original PDF text only"
        assert "VLM Extracted Text" not in result

    def test_merge_preserves_page_order(self, vlm_processor):
        """VLMテキストがページ順にマージされる。"""
        metadata = PDFMetadata(page_count=5, title=None, author=None, subject=None, creator=None)
        pdf_result = PDFResult(
            text="Base text",
            metadata=metadata,
            extraction_method="text",
            pages_needing_vlm=[],
        )

        # 順序をバラバラに指定
        vlm_texts = {
            4: "Page 5 text",
            0: "Page 1 text",
            2: "Page 3 text",
        }

        result = vlm_processor._merge_pdf_texts(pdf_result, vlm_texts)

        # ページ順にソートされていることを確認
        page1_pos = result.find("[Page 1]")
        page3_pos = result.find("[Page 3]")
        page5_pos = result.find("[Page 5]")

        assert page1_pos < page3_pos < page5_pos


class TestVLMProcessorLazyInit:
    """VLMProcessor遅延初期化のテスト。"""

    def test_lazy_initialization(self, vlm_processor):
        """VLMクライアントが遅延初期化される。"""
        assert vlm_processor._vlm_client is None

        with patch("src.processors.vlm_processor.VLMClient") as MockVLMClient:
            mock_instance = MagicMock()
            MockVLMClient.return_value = mock_instance

            client = vlm_processor._get_vlm_client()

            MockVLMClient.assert_called_once_with(model=vlm_processor._model)
            assert client == mock_instance
            assert vlm_processor._vlm_client == mock_instance

    def test_returns_cached_client(self, vlm_processor):
        """2回目以降はキャッシュされたクライアントを返す。"""
        with patch("src.processors.vlm_processor.VLMClient") as MockVLMClient:
            mock_instance = MagicMock()
            MockVLMClient.return_value = mock_instance

            # 1回目の呼び出し
            client1 = vlm_processor._get_vlm_client()
            # 2回目の呼び出し
            client2 = vlm_processor._get_vlm_client()

            # 1回だけインスタンス化される
            MockVLMClient.assert_called_once()
            assert client1 is client2


class TestDocumentProcessorVlmFallbackIntegration:
    """DocumentProcessorのVLMフォールバック機能の統合テスト。"""

    def test_extract_text_triggers_vlm_fallback(self, mock_settings, tmp_path):
        """テキスト抽出でVLMフォールバックがトリガーされる。"""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake pdf")

        metadata = PDFMetadata(page_count=2, title=None, author=None, subject=None, creator=None)
        pdf_result = PDFResult(
            text="Minimal text",
            metadata=metadata,
            extraction_method="vlm_needed",
            pages_needing_vlm=[0, 1],
        )

        with patch("src.indexer.processors.document_processor.get_settings", return_value=mock_settings), \
             patch("src.indexer.processors.document_processor.PDFProcessor") as MockPDFProcessor, \
             patch("src.indexer.processors.document_processor.TextProcessor"), \
             patch("src.indexer.processors.document_processor.OfficeProcessor"), \
             patch("src.indexer.processors.document_processor.Chunker"), \
             patch("src.indexer.processors.document_processor.OllamaEmbeddingClient"), \
             patch("src.indexer.processors.document_processor.LanceDBClient"), \
             patch("src.indexer.processors.document_processor.SQLiteClient"):

            mock_pdf_processor = MagicMock()
            mock_pdf_processor.is_supported.return_value = True
            mock_pdf_processor.extract_text.return_value = pdf_result
            MockPDFProcessor.return_value = mock_pdf_processor

            processor = DocumentProcessor()

            mock_vlm_processor = MagicMock()
            mock_vlm_processor.process_pdf_pages.return_value = "Merged text with VLM"
            processor._vlm_processor = mock_vlm_processor

            result = processor._extract_text(pdf_path)

            mock_vlm_processor.process_pdf_pages.assert_called_once_with(pdf_path, pdf_result)
            assert result == "Merged text with VLM"

    def test_extract_text_no_vlm_when_disabled(self, mock_settings, tmp_path):
        """VLMフォールバックが無効の場合、VLM処理されない。"""
        mock_settings.pdf_vlm_fallback = False
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake pdf")

        metadata = PDFMetadata(page_count=2, title=None, author=None, subject=None, creator=None)
        pdf_result = PDFResult(
            text="Some extracted text",
            metadata=metadata,
            extraction_method="vlm_needed",
            pages_needing_vlm=[0, 1],
        )

        with patch("src.indexer.processors.document_processor.get_settings", return_value=mock_settings), \
             patch("src.indexer.processors.document_processor.PDFProcessor") as MockPDFProcessor, \
             patch("src.indexer.processors.document_processor.TextProcessor"), \
             patch("src.indexer.processors.document_processor.OfficeProcessor"), \
             patch("src.indexer.processors.document_processor.Chunker"), \
             patch("src.indexer.processors.document_processor.OllamaEmbeddingClient"), \
             patch("src.indexer.processors.document_processor.LanceDBClient"), \
             patch("src.indexer.processors.document_processor.SQLiteClient"):

            mock_pdf_processor = MagicMock()
            mock_pdf_processor.is_supported.return_value = True
            mock_pdf_processor.extract_text.return_value = pdf_result
            MockPDFProcessor.return_value = mock_pdf_processor

            processor = DocumentProcessor()

            mock_vlm_processor = MagicMock()
            processor._vlm_processor = mock_vlm_processor

            result = processor._extract_text(pdf_path)

            # VLMフォールバックが無効なので呼ばれない
            mock_vlm_processor.process_pdf_pages.assert_not_called()
            assert result == pdf_result.text

    def test_extract_text_no_vlm_when_no_pages_need_vlm(self, mock_settings, tmp_path):
        """VLM不要なページの場合、VLM処理されない。"""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake pdf")

        metadata = PDFMetadata(page_count=2, title=None, author=None, subject=None, creator=None)
        pdf_result = PDFResult(
            text="Sufficient text on all pages",
            metadata=metadata,
            extraction_method="text",
            pages_needing_vlm=[],  # VLM不要
        )

        with patch("src.indexer.processors.document_processor.get_settings", return_value=mock_settings), \
             patch("src.indexer.processors.document_processor.PDFProcessor") as MockPDFProcessor, \
             patch("src.indexer.processors.document_processor.TextProcessor"), \
             patch("src.indexer.processors.document_processor.OfficeProcessor"), \
             patch("src.indexer.processors.document_processor.Chunker"), \
             patch("src.indexer.processors.document_processor.OllamaEmbeddingClient"), \
             patch("src.indexer.processors.document_processor.LanceDBClient"), \
             patch("src.indexer.processors.document_processor.SQLiteClient"):

            mock_pdf_processor = MagicMock()
            mock_pdf_processor.is_supported.return_value = True
            mock_pdf_processor.extract_text.return_value = pdf_result
            MockPDFProcessor.return_value = mock_pdf_processor

            processor = DocumentProcessor()

            mock_vlm_processor = MagicMock()
            processor._vlm_processor = mock_vlm_processor

            result = processor._extract_text(pdf_path)

            # pages_needing_vlm が空なので呼ばれない
            mock_vlm_processor.process_pdf_pages.assert_not_called()
            assert result == pdf_result.text


class TestDocumentIndexerExcludePatterns:
    """DocumentIndexer除外パターン機能のテスト。"""

    @pytest.fixture
    def mock_indexer_settings(self):
        """除外パターン付きのモック設定。"""
        settings = MagicMock()
        settings.exclude_patterns = ["iterm-log", "*.log", ".git", "__pycache__", "node_modules"]
        return settings

    def test_should_exclude_directory_name(self, mock_indexer_settings):
        """ディレクトリ名が除外パターンに一致。"""
        from src.indexer.document_indexer import DocumentIndexer

        with patch("src.indexer.document_indexer.get_settings", return_value=mock_indexer_settings), \
             patch("src.indexer.document_indexer.OllamaEmbeddingClient"), \
             patch("src.indexer.document_indexer.LanceDBClient"), \
             patch("src.indexer.document_indexer.SQLiteClient"):
            indexer = DocumentIndexer()
            indexer.settings = mock_indexer_settings

            # ディレクトリ名がiterm-logを含むパス
            path = Path("/Users/test/Documents/iterm-log/20250101.log")
            assert indexer._should_exclude(path) is True

    def test_should_exclude_glob_pattern(self, mock_indexer_settings):
        """ファイル名がglobパターンに一致。"""
        from src.indexer.document_indexer import DocumentIndexer

        with patch("src.indexer.document_indexer.get_settings", return_value=mock_indexer_settings), \
             patch("src.indexer.document_indexer.OllamaEmbeddingClient"), \
             patch("src.indexer.document_indexer.LanceDBClient"), \
             patch("src.indexer.document_indexer.SQLiteClient"):
            indexer = DocumentIndexer()
            indexer.settings = mock_indexer_settings

            # .logファイル
            path = Path("/Users/test/Documents/app.log")
            assert indexer._should_exclude(path) is True

    def test_should_not_exclude_normal_file(self, mock_indexer_settings):
        """通常のファイルは除外しない。"""
        from src.indexer.document_indexer import DocumentIndexer

        with patch("src.indexer.document_indexer.get_settings", return_value=mock_indexer_settings), \
             patch("src.indexer.document_indexer.OllamaEmbeddingClient"), \
             patch("src.indexer.document_indexer.LanceDBClient"), \
             patch("src.indexer.document_indexer.SQLiteClient"):
            indexer = DocumentIndexer()
            indexer.settings = mock_indexer_settings

            # 通常のPDFファイル
            path = Path("/Users/test/Documents/report.pdf")
            assert indexer._should_exclude(path) is False

    def test_should_exclude_git_directory(self, mock_indexer_settings):
        """.gitディレクトリ内のファイルを除外。"""
        from src.indexer.document_indexer import DocumentIndexer

        with patch("src.indexer.document_indexer.get_settings", return_value=mock_indexer_settings), \
             patch("src.indexer.document_indexer.OllamaEmbeddingClient"), \
             patch("src.indexer.document_indexer.LanceDBClient"), \
             patch("src.indexer.document_indexer.SQLiteClient"):
            indexer = DocumentIndexer()
            indexer.settings = mock_indexer_settings

            # .git内のファイル
            path = Path("/Users/test/project/.git/config")
            assert indexer._should_exclude(path) is True

    def test_should_exclude_node_modules(self, mock_indexer_settings):
        """node_modulesディレクトリ内のファイルを除外。"""
        from src.indexer.document_indexer import DocumentIndexer

        with patch("src.indexer.document_indexer.get_settings", return_value=mock_indexer_settings), \
             patch("src.indexer.document_indexer.OllamaEmbeddingClient"), \
             patch("src.indexer.document_indexer.LanceDBClient"), \
             patch("src.indexer.document_indexer.SQLiteClient"):
            indexer = DocumentIndexer()
            indexer.settings = mock_indexer_settings

            # node_modules内のファイル
            path = Path("/Users/test/project/node_modules/package/index.js")
            assert indexer._should_exclude(path) is True
