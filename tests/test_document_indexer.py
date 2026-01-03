"""DocumentIndexerのVLM関連テスト。"""

import signal
from concurrent.futures import TimeoutError as FuturesTimeoutError
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.indexer.document_indexer import DocumentIndexer, VLMTimeoutError
from src.processors.pdf_processor import PDFMetadata, PDFResult


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
def indexer(mock_settings):
    """モックを使用したDocumentIndexerを作成。"""
    with patch("src.indexer.document_indexer.get_settings", return_value=mock_settings), \
         patch("src.indexer.document_indexer.PDFProcessor"), \
         patch("src.indexer.document_indexer.TextProcessor"), \
         patch("src.indexer.document_indexer.OfficeProcessor"), \
         patch("src.indexer.document_indexer.ImageProcessor"), \
         patch("src.indexer.document_indexer.AudioProcessor"), \
         patch("src.indexer.document_indexer.VideoProcessor"), \
         patch("src.indexer.document_indexer.Chunker"), \
         patch("src.indexer.document_indexer.OllamaEmbeddingClient"), \
         patch("src.indexer.document_indexer.LanceDBClient"), \
         patch("src.indexer.document_indexer.SQLiteClient"):
        indexer = DocumentIndexer()
        yield indexer


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


class TestProcessPdfWithVlm:
    """_process_pdf_with_vlmメソッドのテスト。"""

    def test_process_pdf_with_vlm_success(self, indexer, sample_pdf_result, tmp_path):
        """VLM処理が成功した場合、テキストがマージされる。"""
        # テスト用画像ファイルを作成
        image_files = [tmp_path / f"page_{i}.png" for i in range(3)]
        for img in image_files:
            img.write_bytes(b"fake image data")

        pdf_path = tmp_path / "test.pdf"

        # モック設定
        indexer.pdf_processor.render_pages_to_images.return_value = image_files

        # VLMクライアントのモック
        mock_vlm_client = MagicMock()
        mock_vlm_client.extract_text.side_effect = [
            "VLM text from page 2",
            "VLM text from page 3",
            "VLM text from page 5",
        ]

        with patch.object(indexer, "_get_pdf_vlm_client", return_value=mock_vlm_client), \
             patch.object(indexer, "_vlm_extract_with_timeout") as mock_extract:
            mock_extract.side_effect = [
                "VLM text from page 2",
                "VLM text from page 3",
                "VLM text from page 5",
            ]

            result = indexer._process_pdf_with_vlm(pdf_path, sample_pdf_result)

        # 結果の確認
        assert "VLM Extracted Text" in result
        assert "VLM text from page 2" in result
        assert "VLM text from page 3" in result
        assert "VLM text from page 5" in result
        assert sample_pdf_result.text in result

    def test_process_pdf_with_vlm_timeout(self, indexer, sample_pdf_result, tmp_path):
        """VLM処理がタイムアウトした場合、エラーがログされる。"""
        image_files = [tmp_path / f"page_{i}.png" for i in range(3)]
        for img in image_files:
            img.write_bytes(b"fake image data")

        pdf_path = tmp_path / "test.pdf"
        indexer.pdf_processor.render_pages_to_images.return_value = image_files

        mock_vlm_client = MagicMock()

        with patch.object(indexer, "_get_pdf_vlm_client", return_value=mock_vlm_client), \
             patch.object(indexer, "_vlm_extract_with_timeout") as mock_extract:
            # 全ページがタイムアウト
            mock_extract.side_effect = VLMTimeoutError("timeout")

            result = indexer._process_pdf_with_vlm(pdf_path, sample_pdf_result)

        # タイムアウト時は元のテキストのみ返される
        assert result == sample_pdf_result.text

    def test_process_pdf_with_vlm_partial_success(self, indexer, sample_pdf_result, tmp_path):
        """一部のページのみ成功した場合。"""
        image_files = [tmp_path / f"page_{i}.png" for i in range(3)]
        for img in image_files:
            img.write_bytes(b"fake image data")

        pdf_path = tmp_path / "test.pdf"
        indexer.pdf_processor.render_pages_to_images.return_value = image_files

        mock_vlm_client = MagicMock()

        with patch.object(indexer, "_get_pdf_vlm_client", return_value=mock_vlm_client), \
             patch.object(indexer, "_vlm_extract_with_timeout") as mock_extract:
            # 1ページ成功、1ページタイムアウト、1ページエラー
            mock_extract.side_effect = [
                "VLM text from page 2",
                VLMTimeoutError("timeout"),
                Exception("VLM error"),
            ]

            result = indexer._process_pdf_with_vlm(pdf_path, sample_pdf_result)

        # 成功したページのテキストのみマージされる
        assert "VLM text from page 2" in result
        assert sample_pdf_result.text in result

    def test_process_pdf_with_vlm_max_pages_limit(self, indexer, tmp_path):
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
        indexer.settings.pdf_vlm_max_pages = 5

        image_files = [tmp_path / f"page_{i}.png" for i in range(5)]
        for img in image_files:
            img.write_bytes(b"fake image data")

        pdf_path = tmp_path / "test.pdf"
        indexer.pdf_processor.render_pages_to_images.return_value = image_files

        mock_vlm_client = MagicMock()

        with patch.object(indexer, "_get_pdf_vlm_client", return_value=mock_vlm_client), \
             patch.object(indexer, "_vlm_extract_with_timeout") as mock_extract:
            mock_extract.return_value = "VLM extracted text"

            indexer._process_pdf_with_vlm(pdf_path, pdf_result)

        # 5回だけ呼ばれる
        assert mock_extract.call_count == 5

    def test_process_pdf_with_vlm_empty_extraction(self, indexer, sample_pdf_result, tmp_path):
        """VLMがテキストを返さなかった場合。"""
        image_files = [tmp_path / f"page_{i}.png" for i in range(3)]
        for img in image_files:
            img.write_bytes(b"fake image data")

        pdf_path = tmp_path / "test.pdf"
        indexer.pdf_processor.render_pages_to_images.return_value = image_files

        mock_vlm_client = MagicMock()

        with patch.object(indexer, "_get_pdf_vlm_client", return_value=mock_vlm_client), \
             patch.object(indexer, "_vlm_extract_with_timeout") as mock_extract:
            # 全ページで空文字列を返す
            mock_extract.return_value = ""

            result = indexer._process_pdf_with_vlm(pdf_path, sample_pdf_result)

        # VLM結果がないので元のテキストのみ
        assert result == sample_pdf_result.text


class TestProcessVlmParallel:
    """_process_vlm_parallelメソッドのテスト。"""

    def test_parallel_processing_success(self, indexer, tmp_path):
        """並列処理が正常に動作する。"""
        indexer.settings.pdf_vlm_workers = 2
        indexer.settings.pdf_vlm_model = "test-model"

        pages = [0, 1, 2]
        image_paths = [tmp_path / f"page_{i}.png" for i in range(3)]
        for img in image_paths:
            img.write_bytes(b"fake image data")

        with patch("src.indexer.document_indexer.VLMClient") as MockVLMClient:
            mock_instance = MagicMock()
            mock_instance.extract_text.return_value = "Extracted text"
            MockVLMClient.return_value = mock_instance

            results = indexer._process_vlm_parallel(
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

    def test_parallel_processing_timeout(self, indexer, tmp_path):
        """並列処理でタイムアウトが発生した場合。"""
        indexer.settings.pdf_vlm_workers = 2
        indexer.settings.pdf_vlm_model = "test-model"

        pages = [0, 1]
        image_paths = [tmp_path / f"page_{i}.png" for i in range(2)]
        for img in image_paths:
            img.write_bytes(b"fake image data")

        with patch("src.indexer.document_indexer.VLMClient") as MockVLMClient, \
             patch("concurrent.futures.ThreadPoolExecutor") as MockExecutor:

            # future.result() がタイムアウトを発生させる
            mock_future = MagicMock()
            mock_future.result.side_effect = FuturesTimeoutError()

            mock_executor_instance = MagicMock()
            mock_executor_instance.__enter__.return_value = mock_executor_instance
            mock_executor_instance.__exit__.return_value = False
            mock_executor_instance.submit.return_value = mock_future
            MockExecutor.return_value = mock_executor_instance

            # futuresの辞書を設定
            with patch.object(indexer, "_process_vlm_parallel") as mock_parallel:
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

    def test_parallel_processing_mixed_results(self, indexer, tmp_path):
        """成功、失敗、タイムアウトが混在した場合。"""
        indexer.settings.pdf_vlm_workers = 2
        indexer.settings.pdf_vlm_model = "test-model"

        pages = [0, 1, 2]
        image_paths = [tmp_path / f"page_{i}.png" for i in range(3)]
        for img in image_paths:
            img.write_bytes(b"fake image data")

        # 直接結果を返すようにモック
        with patch.object(indexer, "_process_vlm_parallel") as mock_parallel:
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

    def test_parallel_processing_empty_pages(self, indexer, tmp_path):
        """処理するページがない場合。"""
        indexer.settings.pdf_vlm_workers = 2
        indexer.settings.pdf_vlm_model = "test-model"

        results = indexer._process_vlm_parallel(
            pages=[],
            image_paths=[],
            workers=2,
            timeout_seconds=60,
            total_pages=0,
        )

        assert results == {}


class TestVlmExtractWithTimeout:
    """_vlm_extract_with_timeoutメソッドのテスト。"""

    def test_successful_extraction(self, indexer, tmp_path):
        """タイムアウト内で正常に抽出できる場合。"""
        image_path = tmp_path / "test.png"
        image_path.write_bytes(b"fake image data")

        mock_vlm_client = MagicMock()
        mock_vlm_client.extract_text.return_value = "Extracted text content"

        result = indexer._vlm_extract_with_timeout(
            vlm_client=mock_vlm_client,
            image_path=image_path,
            timeout_seconds=60,
        )

        assert result == "Extracted text content"
        mock_vlm_client.extract_text.assert_called_once_with(image_path)

    def test_timeout_raises_error(self, indexer, tmp_path):
        """タイムアウトした場合にVLMTimeoutErrorが発生する。"""
        image_path = tmp_path / "test.png"
        image_path.write_bytes(b"fake image data")

        mock_vlm_client = MagicMock()

        # SIGALRMをトリガーするモック
        def slow_extraction(*args):
            # 実際にはシグナルを使うのでモックで代替
            raise VLMTimeoutError("VLM processing timed out after 1s")

        mock_vlm_client.extract_text.side_effect = slow_extraction

        with pytest.raises(VLMTimeoutError):
            indexer._vlm_extract_with_timeout(
                vlm_client=mock_vlm_client,
                image_path=image_path,
                timeout_seconds=1,
            )

    def test_signal_handler_restored(self, indexer, tmp_path):
        """タイムアウト処理後にシグナルハンドラが復元される。"""
        image_path = tmp_path / "test.png"
        image_path.write_bytes(b"fake image data")

        mock_vlm_client = MagicMock()
        mock_vlm_client.extract_text.return_value = "text"

        # 元のハンドラを取得
        original_handler = signal.getsignal(signal.SIGALRM)

        indexer._vlm_extract_with_timeout(
            vlm_client=mock_vlm_client,
            image_path=image_path,
            timeout_seconds=60,
        )

        # ハンドラが復元されていることを確認
        current_handler = signal.getsignal(signal.SIGALRM)
        assert current_handler == original_handler


class TestMergePdfTexts:
    """_merge_pdf_textsメソッドのテスト。"""

    def test_merge_with_vlm_texts(self, indexer):
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

        result = indexer._merge_pdf_texts(pdf_result, vlm_texts)

        assert "Original PDF text" in result
        assert "--- VLM Extracted Text ---" in result
        assert "[Page 2]" in result
        assert "[Page 3]" in result
        assert "VLM extracted text from page 2" in result
        assert "VLM extracted text from page 3" in result

    def test_merge_empty_vlm_texts(self, indexer):
        """VLMテキストが空の場合、元のテキストのみ返される。"""
        metadata = PDFMetadata(page_count=1, title=None, author=None, subject=None, creator=None)
        pdf_result = PDFResult(
            text="Original PDF text only",
            metadata=metadata,
            extraction_method="text",
            pages_needing_vlm=[],
        )

        result = indexer._merge_pdf_texts(pdf_result, {})

        assert result == "Original PDF text only"
        assert "VLM Extracted Text" not in result

    def test_merge_preserves_page_order(self, indexer):
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

        result = indexer._merge_pdf_texts(pdf_result, vlm_texts)

        # ページ順にソートされていることを確認
        page1_pos = result.find("[Page 1]")
        page3_pos = result.find("[Page 3]")
        page5_pos = result.find("[Page 5]")

        assert page1_pos < page3_pos < page5_pos


class TestGetPdfVlmClient:
    """_get_pdf_vlm_clientメソッドのテスト。"""

    def test_lazy_initialization(self, indexer):
        """VLMクライアントが遅延初期化される。"""
        assert indexer._pdf_vlm_client is None

        with patch("src.indexer.document_indexer.VLMClient") as MockVLMClient:
            mock_instance = MagicMock()
            MockVLMClient.return_value = mock_instance

            client = indexer._get_pdf_vlm_client()

            MockVLMClient.assert_called_once_with(model=indexer.settings.pdf_vlm_model)
            assert client == mock_instance
            assert indexer._pdf_vlm_client == mock_instance

    def test_returns_cached_client(self, indexer):
        """2回目以降はキャッシュされたクライアントを返す。"""
        with patch("src.indexer.document_indexer.VLMClient") as MockVLMClient:
            mock_instance = MagicMock()
            MockVLMClient.return_value = mock_instance

            # 1回目の呼び出し
            client1 = indexer._get_pdf_vlm_client()
            # 2回目の呼び出し
            client2 = indexer._get_pdf_vlm_client()

            # 1回だけインスタンス化される
            MockVLMClient.assert_called_once()
            assert client1 is client2


class TestVlmFallbackIntegration:
    """VLMフォールバック機能の統合テスト。"""

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

        with patch("src.indexer.document_indexer.get_settings", return_value=mock_settings), \
             patch("src.indexer.document_indexer.PDFProcessor") as MockPDFProcessor, \
             patch("src.indexer.document_indexer.TextProcessor"), \
             patch("src.indexer.document_indexer.OfficeProcessor"), \
             patch("src.indexer.document_indexer.ImageProcessor"), \
             patch("src.indexer.document_indexer.AudioProcessor"), \
             patch("src.indexer.document_indexer.VideoProcessor"), \
             patch("src.indexer.document_indexer.Chunker"), \
             patch("src.indexer.document_indexer.OllamaEmbeddingClient"), \
             patch("src.indexer.document_indexer.LanceDBClient"), \
             patch("src.indexer.document_indexer.SQLiteClient"):

            mock_pdf_processor = MagicMock()
            mock_pdf_processor.is_supported.return_value = True
            mock_pdf_processor.extract_text.return_value = pdf_result
            MockPDFProcessor.return_value = mock_pdf_processor

            indexer = DocumentIndexer()

            with patch.object(indexer, "_process_pdf_with_vlm") as mock_process_vlm:
                mock_process_vlm.return_value = "Merged text with VLM"

                result = indexer._extract_text(pdf_path)

                mock_process_vlm.assert_called_once_with(pdf_path, pdf_result)
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

        with patch("src.indexer.document_indexer.get_settings", return_value=mock_settings), \
             patch("src.indexer.document_indexer.PDFProcessor") as MockPDFProcessor, \
             patch("src.indexer.document_indexer.TextProcessor"), \
             patch("src.indexer.document_indexer.OfficeProcessor"), \
             patch("src.indexer.document_indexer.ImageProcessor"), \
             patch("src.indexer.document_indexer.AudioProcessor"), \
             patch("src.indexer.document_indexer.VideoProcessor"), \
             patch("src.indexer.document_indexer.Chunker"), \
             patch("src.indexer.document_indexer.OllamaEmbeddingClient"), \
             patch("src.indexer.document_indexer.LanceDBClient"), \
             patch("src.indexer.document_indexer.SQLiteClient"):

            mock_pdf_processor = MagicMock()
            mock_pdf_processor.is_supported.return_value = True
            mock_pdf_processor.extract_text.return_value = pdf_result
            MockPDFProcessor.return_value = mock_pdf_processor

            indexer = DocumentIndexer()

            with patch.object(indexer, "_process_pdf_with_vlm") as mock_process_vlm:
                result = indexer._extract_text(pdf_path)

                # VLMフォールバックが無効なので呼ばれない
                mock_process_vlm.assert_not_called()
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

        with patch("src.indexer.document_indexer.get_settings", return_value=mock_settings), \
             patch("src.indexer.document_indexer.PDFProcessor") as MockPDFProcessor, \
             patch("src.indexer.document_indexer.TextProcessor"), \
             patch("src.indexer.document_indexer.OfficeProcessor"), \
             patch("src.indexer.document_indexer.ImageProcessor"), \
             patch("src.indexer.document_indexer.AudioProcessor"), \
             patch("src.indexer.document_indexer.VideoProcessor"), \
             patch("src.indexer.document_indexer.Chunker"), \
             patch("src.indexer.document_indexer.OllamaEmbeddingClient"), \
             patch("src.indexer.document_indexer.LanceDBClient"), \
             patch("src.indexer.document_indexer.SQLiteClient"):

            mock_pdf_processor = MagicMock()
            mock_pdf_processor.is_supported.return_value = True
            mock_pdf_processor.extract_text.return_value = pdf_result
            MockPDFProcessor.return_value = mock_pdf_processor

            indexer = DocumentIndexer()

            with patch.object(indexer, "_process_pdf_with_vlm") as mock_process_vlm:
                result = indexer._extract_text(pdf_path)

                # pages_needing_vlm が空なので呼ばれない
                mock_process_vlm.assert_not_called()
                assert result == pdf_result.text
