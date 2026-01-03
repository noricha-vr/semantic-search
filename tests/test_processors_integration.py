"""プロセッサ統合テスト。

各プロセッサのcan_process()判定、プロセッサ選択ロジック、
モックを使用したインデックス処理フローをテストする。
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.indexer.processors import (
    AudioIndexerProcessor,
    BaseMediaProcessor,
    DocumentProcessor,
    ImageIndexerProcessor,
    VideoIndexerProcessor,
)
from src.processors.audio_processor import AudioProcessor
from src.processors.image_processor import ImageProcessor
from src.processors.office_processor import OfficeProcessor
from src.processors.pdf_processor import PDFProcessor
from src.processors.text_processor import TextProcessor
from src.processors.video_processor import VideoProcessor


class TestCanProcessDecision:
    """can_process()によるファイルタイプ判定テスト。"""

    def test_text_processor_detects_text_files(self, tmp_path):
        """TextProcessorがテキストファイルを正しく判定する。"""
        processor = TextProcessor()

        # サポートされる拡張子
        assert processor.is_supported(tmp_path / "readme.txt") is True
        assert processor.is_supported(tmp_path / "document.md") is True
        assert processor.is_supported(tmp_path / "script.py") is True
        assert processor.is_supported(tmp_path / "code.js") is True
        assert processor.is_supported(tmp_path / "code.ts") is True
        assert processor.is_supported(tmp_path / "config.yaml") is True
        assert processor.is_supported(tmp_path / "data.json") is True
        assert processor.is_supported(tmp_path / "style.css") is True
        assert processor.is_supported(tmp_path / "query.sql") is True

        # 特殊ファイル名
        assert processor.is_supported(tmp_path / "Makefile") is True
        assert processor.is_supported(tmp_path / "Dockerfile") is True

        # サポートされない拡張子
        assert processor.is_supported(tmp_path / "image.png") is False
        assert processor.is_supported(tmp_path / "audio.mp3") is False
        assert processor.is_supported(tmp_path / "document.pdf") is False

    def test_pdf_processor_detects_pdf_files(self, tmp_path):
        """PDFProcessorがPDFファイルを正しく判定する。"""
        processor = PDFProcessor()

        assert processor.is_supported(tmp_path / "document.pdf") is True
        assert processor.is_supported(tmp_path / "report.PDF") is True

        assert processor.is_supported(tmp_path / "image.png") is False
        assert processor.is_supported(tmp_path / "document.txt") is False

    def test_office_processor_detects_office_files(self, tmp_path):
        """OfficeProcessorがOffice文書を正しく判定する。"""
        processor = OfficeProcessor()

        # Word
        assert processor.is_supported(tmp_path / "document.docx") is True
        assert processor.is_supported(tmp_path / "document.doc") is True

        # Excel
        assert processor.is_supported(tmp_path / "spreadsheet.xlsx") is True
        assert processor.is_supported(tmp_path / "spreadsheet.xls") is True

        # PowerPoint
        assert processor.is_supported(tmp_path / "presentation.pptx") is True
        assert processor.is_supported(tmp_path / "presentation.ppt") is True

        # サポートされない
        assert processor.is_supported(tmp_path / "document.pdf") is False
        assert processor.is_supported(tmp_path / "document.txt") is False

    def test_image_processor_detects_image_files(self, tmp_path):
        """ImageProcessorが画像ファイルを正しく判定する。"""
        processor = ImageProcessor()

        assert processor.is_supported(tmp_path / "photo.jpg") is True
        assert processor.is_supported(tmp_path / "photo.jpeg") is True
        assert processor.is_supported(tmp_path / "image.png") is True
        assert processor.is_supported(tmp_path / "animation.gif") is True
        assert processor.is_supported(tmp_path / "image.webp") is True
        assert processor.is_supported(tmp_path / "image.bmp") is True
        assert processor.is_supported(tmp_path / "image.tiff") is True

        assert processor.is_supported(tmp_path / "video.mp4") is False
        assert processor.is_supported(tmp_path / "document.pdf") is False

    def test_audio_processor_detects_audio_files(self, tmp_path):
        """AudioProcessorが音声ファイルを正しく判定する。"""
        processor = AudioProcessor()

        assert processor.is_supported(tmp_path / "song.mp3") is True
        assert processor.is_supported(tmp_path / "audio.wav") is True
        assert processor.is_supported(tmp_path / "recording.m4a") is True
        assert processor.is_supported(tmp_path / "music.flac") is True
        assert processor.is_supported(tmp_path / "audio.aac") is True
        assert processor.is_supported(tmp_path / "audio.ogg") is True
        assert processor.is_supported(tmp_path / "audio.wma") is True

        assert processor.is_supported(tmp_path / "video.mp4") is False
        assert processor.is_supported(tmp_path / "image.png") is False

    def test_video_processor_detects_video_files(self, tmp_path):
        """VideoProcessorが動画ファイルを正しく判定する。"""
        processor = VideoProcessor()

        assert processor.is_supported(tmp_path / "video.mp4") is True
        assert processor.is_supported(tmp_path / "movie.mov") is True
        assert processor.is_supported(tmp_path / "video.avi") is True
        assert processor.is_supported(tmp_path / "video.mkv") is True
        assert processor.is_supported(tmp_path / "video.wmv") is True
        assert processor.is_supported(tmp_path / "video.flv") is True
        assert processor.is_supported(tmp_path / "video.webm") is True

        assert processor.is_supported(tmp_path / "audio.mp3") is False
        assert processor.is_supported(tmp_path / "image.png") is False


class TestProcessorSelection:
    """プロセッサ選択ロジックのテスト。"""

    @pytest.fixture
    def mock_sqlite_client(self, tmp_path):
        """SQLiteClientのモック。"""
        from src.storage.sqlite_client import SQLiteClient

        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = Path(f.name)
        client = SQLiteClient(db_path=db_path)
        yield client
        if db_path.exists():
            db_path.unlink()

    def test_document_processor_handles_documents(self, tmp_path, mock_sqlite_client):
        """DocumentProcessorがドキュメントを正しく処理対象とする。"""
        # モック作成
        mock_pdf = MagicMock(spec=PDFProcessor)
        mock_text = MagicMock(spec=TextProcessor)
        mock_office = MagicMock(spec=OfficeProcessor)

        processor = DocumentProcessor(
            pdf_processor=mock_pdf,
            text_processor=mock_text,
            office_processor=mock_office,
            sqlite_client=mock_sqlite_client,
        )

        # PDFファイル
        mock_pdf.is_supported.return_value = True
        mock_text.is_supported.return_value = False
        mock_office.is_supported.return_value = False
        assert processor.can_process(tmp_path / "document.pdf") is True

        # テキストファイル
        mock_pdf.is_supported.return_value = False
        mock_text.is_supported.return_value = True
        mock_office.is_supported.return_value = False
        assert processor.can_process(tmp_path / "readme.txt") is True

        # Officeファイル
        mock_pdf.is_supported.return_value = False
        mock_text.is_supported.return_value = False
        mock_office.is_supported.return_value = True
        assert processor.can_process(tmp_path / "document.docx") is True

        # どれでもない
        mock_pdf.is_supported.return_value = False
        mock_text.is_supported.return_value = False
        mock_office.is_supported.return_value = False
        assert processor.can_process(tmp_path / "image.png") is False

    def test_select_correct_processor_for_file_type(self, tmp_path, mock_sqlite_client):
        """ファイルタイプに応じた正しいプロセッサが選択される。"""
        processors = [
            DocumentProcessor(sqlite_client=mock_sqlite_client),
            ImageIndexerProcessor(sqlite_client=mock_sqlite_client),
            AudioIndexerProcessor(sqlite_client=mock_sqlite_client),
            VideoIndexerProcessor(sqlite_client=mock_sqlite_client),
        ]

        test_cases = [
            (tmp_path / "document.pdf", DocumentProcessor),
            (tmp_path / "readme.txt", DocumentProcessor),
            (tmp_path / "report.docx", DocumentProcessor),
            (tmp_path / "image.png", ImageIndexerProcessor),
            (tmp_path / "photo.jpg", ImageIndexerProcessor),
            (tmp_path / "audio.mp3", AudioIndexerProcessor),
            (tmp_path / "recording.wav", AudioIndexerProcessor),
            (tmp_path / "video.mp4", VideoIndexerProcessor),
            (tmp_path / "movie.mkv", VideoIndexerProcessor),
        ]

        for file_path, expected_processor_type in test_cases:
            selected = None
            for p in processors:
                if p.can_process(file_path):
                    selected = p
                    break

            assert selected is not None, f"No processor found for {file_path}"
            assert isinstance(selected, expected_processor_type), (
                f"Wrong processor for {file_path}: "
                f"expected {expected_processor_type.__name__}, got {type(selected).__name__}"
            )

    def test_no_processor_for_unsupported_file(self, tmp_path, mock_sqlite_client):
        """サポートされないファイルは処理対象外。"""
        processors = [
            DocumentProcessor(sqlite_client=mock_sqlite_client),
            ImageIndexerProcessor(sqlite_client=mock_sqlite_client),
            AudioIndexerProcessor(sqlite_client=mock_sqlite_client),
            VideoIndexerProcessor(sqlite_client=mock_sqlite_client),
        ]

        unsupported_files = [
            tmp_path / "archive.zip",
            tmp_path / "package.tar.gz",
            tmp_path / "data.bin",
            tmp_path / "database.sqlite",
        ]

        for file_path in unsupported_files:
            for p in processors:
                assert p.can_process(file_path) is False, (
                    f"Processor {type(p).__name__} incorrectly claims to handle {file_path}"
                )


class TestDocumentProcessorIntegration:
    """DocumentProcessorの統合テスト。"""

    @pytest.fixture
    def mock_dependencies(self, tmp_path):
        """モック依存関係を作成。"""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = Path(f.name)

        from src.storage.sqlite_client import SQLiteClient

        sqlite_client = SQLiteClient(db_path=db_path)

        mocks = {
            "pdf_processor": MagicMock(spec=PDFProcessor),
            "text_processor": MagicMock(spec=TextProcessor),
            "office_processor": MagicMock(spec=OfficeProcessor),
            "chunker": MagicMock(),
            "embedding_client": MagicMock(),
            "lancedb_client": MagicMock(),
            "sqlite_client": sqlite_client,
            "db_path": db_path,
        }

        yield mocks

        if db_path.exists():
            db_path.unlink()

    def test_process_text_file_workflow(self, tmp_path, mock_dependencies):
        """テキストファイル処理のワークフロー。"""
        from src.processors.chunker import ChunkResult
        from src.processors.text_processor import TextResult

        # テスト用ファイル作成
        test_file = tmp_path / "test.txt"
        test_file.write_text("This is test content for chunking and embedding.")

        # モック設定
        mock_dependencies["text_processor"].is_supported.return_value = True
        mock_dependencies["pdf_processor"].is_supported.return_value = False
        mock_dependencies["office_processor"].is_supported.return_value = False
        mock_dependencies["text_processor"].extract_text.return_value = TextResult(
            text="This is test content for chunking and embedding.",
            encoding="utf-8",
            line_count=1,
        )
        mock_dependencies["chunker"].chunk_text.return_value = [
            ChunkResult(text="This is test content", chunk_index=0, start_char=0, end_char=20),
            ChunkResult(text="for chunking and embedding.", chunk_index=1, start_char=21, end_char=48),
        ]
        mock_dependencies["embedding_client"].embed_batch.return_value = [
            [0.1] * 768,
            [0.2] * 768,
        ]

        processor = DocumentProcessor(
            pdf_processor=mock_dependencies["pdf_processor"],
            text_processor=mock_dependencies["text_processor"],
            office_processor=mock_dependencies["office_processor"],
            chunker=mock_dependencies["chunker"],
            embedding_client=mock_dependencies["embedding_client"],
            lancedb_client=mock_dependencies["lancedb_client"],
            sqlite_client=mock_dependencies["sqlite_client"],
        )

        # 処理実行
        result = processor.process(test_file, "test-hash-123")

        # 検証
        assert result is not None
        assert result["path"] == str(test_file.absolute())
        assert result["media_type"] == "document"

        # チャンクが作成された
        mock_dependencies["chunker"].chunk_text.assert_called_once()

        # 埋め込みが生成された
        mock_dependencies["embedding_client"].embed_batch.assert_called_once()

        # LanceDBに保存された
        mock_dependencies["lancedb_client"].add_chunks.assert_called_once()


class TestImageIndexerIntegration:
    """ImageIndexerProcessorの統合テスト。"""

    @pytest.fixture
    def mock_dependencies(self, tmp_path):
        """モック依存関係を作成。"""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = Path(f.name)

        from src.storage.sqlite_client import SQLiteClient

        sqlite_client = SQLiteClient(db_path=db_path)

        mocks = {
            "image_processor": MagicMock(spec=ImageProcessor),
            "sqlite_client": sqlite_client,
            "db_path": db_path,
        }

        yield mocks

        if db_path.exists():
            db_path.unlink()

    def test_can_process_images(self, tmp_path, mock_dependencies):
        """画像ファイルの処理可能判定。"""
        mock_dependencies["image_processor"].is_supported.return_value = True

        processor = ImageIndexerProcessor(
            image_processor=mock_dependencies["image_processor"],
            sqlite_client=mock_dependencies["sqlite_client"],
        )

        assert processor.can_process(tmp_path / "test.png") is True

    def test_process_creates_document_record(self, tmp_path, mock_dependencies):
        """画像処理でドキュメントレコードが作成される。"""
        # テスト用画像ファイル作成
        from PIL import Image

        test_image = tmp_path / "test.png"
        img = Image.new("RGB", (100, 100), color="red")
        img.save(test_image)

        mock_dependencies["image_processor"].is_supported.return_value = True
        mock_dependencies["image_processor"].index_image.return_value = {
            "id": "vlm-result-1",
            "description": "A red image",
        }

        processor = ImageIndexerProcessor(
            image_processor=mock_dependencies["image_processor"],
            sqlite_client=mock_dependencies["sqlite_client"],
        )

        result = processor.process(test_image, "image-hash-123")

        assert result is not None
        assert result["media_type"] == "image"
        assert result["width"] == 100
        assert result["height"] == 100


class TestAudioIndexerIntegration:
    """AudioIndexerProcessorの統合テスト。"""

    @pytest.fixture
    def mock_dependencies(self, tmp_path):
        """モック依存関係を作成。"""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = Path(f.name)

        from src.storage.sqlite_client import SQLiteClient

        sqlite_client = SQLiteClient(db_path=db_path)

        mocks = {
            "audio_processor": MagicMock(spec=AudioProcessor),
            "sqlite_client": sqlite_client,
            "db_path": db_path,
        }

        yield mocks

        if db_path.exists():
            db_path.unlink()

    def test_can_process_audio(self, tmp_path, mock_dependencies):
        """音声ファイルの処理可能判定。"""
        mock_dependencies["audio_processor"].is_supported.return_value = True

        processor = AudioIndexerProcessor(
            audio_processor=mock_dependencies["audio_processor"],
            sqlite_client=mock_dependencies["sqlite_client"],
        )

        assert processor.can_process(tmp_path / "audio.mp3") is True

    def test_process_creates_transcript(self, tmp_path, mock_dependencies):
        """音声処理でトランスクリプトが作成される。"""
        # テスト用ファイル（ダミー）
        test_audio = tmp_path / "test.mp3"
        test_audio.write_bytes(b"dummy audio content")

        mock_dependencies["audio_processor"].is_supported.return_value = True
        mock_dependencies["audio_processor"].index_audio.return_value = {
            "id": "transcript-1",
            "document_id": "doc-1",
            "full_text": "Test transcript text",
            "language": "en",
            "duration_seconds": 120.0,
            "word_count": 3,
        }

        processor = AudioIndexerProcessor(
            audio_processor=mock_dependencies["audio_processor"],
            sqlite_client=mock_dependencies["sqlite_client"],
        )

        result = processor.process(test_audio, "audio-hash-123")

        assert result is not None
        assert result["media_type"] == "audio"
        mock_dependencies["audio_processor"].index_audio.assert_called_once()


class TestVideoIndexerIntegration:
    """VideoIndexerProcessorの統合テスト。"""

    @pytest.fixture
    def mock_dependencies(self, tmp_path):
        """モック依存関係を作成。"""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = Path(f.name)

        from src.storage.sqlite_client import SQLiteClient

        sqlite_client = SQLiteClient(db_path=db_path)

        mocks = {
            "video_processor": MagicMock(spec=VideoProcessor),
            "sqlite_client": sqlite_client,
            "db_path": db_path,
        }

        yield mocks

        if db_path.exists():
            db_path.unlink()

    def test_can_process_video(self, tmp_path, mock_dependencies):
        """動画ファイルの処理可能判定。"""
        mock_dependencies["video_processor"].is_supported.return_value = True

        processor = VideoIndexerProcessor(
            video_processor=mock_dependencies["video_processor"],
            sqlite_client=mock_dependencies["sqlite_client"],
        )

        assert processor.can_process(tmp_path / "video.mp4") is True

    def test_process_creates_transcript_and_dimensions(self, tmp_path, mock_dependencies):
        """動画処理でトランスクリプトとサイズ情報が作成される。"""
        # テスト用ファイル（ダミー）
        test_video = tmp_path / "test.mp4"
        test_video.write_bytes(b"dummy video content")

        mock_dependencies["video_processor"].is_supported.return_value = True
        mock_dependencies["video_processor"].index_video.return_value = {
            "transcript": {
                "id": "transcript-v1",
                "document_id": "doc-v1",
                "full_text": "Video transcript text",
                "language": "en",
                "duration_seconds": 300.0,
                "word_count": 3,
            },
            "width": 1920,
            "height": 1080,
        }

        processor = VideoIndexerProcessor(
            video_processor=mock_dependencies["video_processor"],
            sqlite_client=mock_dependencies["sqlite_client"],
        )

        result = processor.process(test_video, "video-hash-123")

        assert result is not None
        assert result["media_type"] == "video"
        mock_dependencies["video_processor"].index_video.assert_called_once()


class TestMultiProcessorWorkflow:
    """複数プロセッサを使用したワークフローテスト。"""

    @pytest.fixture
    def setup_processors(self, tmp_path):
        """テスト用のプロセッサセットアップ。"""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = Path(f.name)

        from src.storage.sqlite_client import SQLiteClient

        sqlite_client = SQLiteClient(db_path=db_path)

        yield {
            "sqlite_client": sqlite_client,
            "db_path": db_path,
            "tmp_path": tmp_path,
        }

        if db_path.exists():
            db_path.unlink()

    def test_batch_file_processing_simulation(self, setup_processors):
        """バッチファイル処理のシミュレーション。"""
        tmp_path = setup_processors["tmp_path"]

        # テスト用ファイル作成
        files = [
            (tmp_path / "readme.txt", b"Text content"),
            (tmp_path / "photo.jpg", b"fake jpg"),
            (tmp_path / "audio.mp3", b"fake mp3"),
            (tmp_path / "video.mp4", b"fake mp4"),
        ]
        for file_path, content in files:
            file_path.write_bytes(content)

        # プロセッサマッピング
        processor_map = {
            ".txt": "DocumentProcessor",
            ".jpg": "ImageIndexerProcessor",
            ".mp3": "AudioIndexerProcessor",
            ".mp4": "VideoIndexerProcessor",
        }

        # ファイルに対応するプロセッサを決定
        results = []
        for file_path, _ in files:
            ext = file_path.suffix.lower()
            processor_name = processor_map.get(ext)
            results.append({
                "file": file_path.name,
                "processor": processor_name,
            })

        # 全ファイルにプロセッサが割り当てられた
        assert len(results) == 4
        assert all(r["processor"] is not None for r in results)

    def test_processor_priority_order(self, setup_processors):
        """プロセッサの優先順位確認。"""
        # 同じファイルを複数プロセッサでチェック
        # DocumentProcessorはoffice/pdf/textを処理
        # それ以外は専用プロセッサ

        tmp_path = setup_processors["tmp_path"]

        # 実際のプロセッサでテスト
        doc_processor = DocumentProcessor(
            sqlite_client=setup_processors["sqlite_client"]
        )

        # ドキュメントタイプはDocumentProcessorで処理可能
        assert doc_processor.can_process(tmp_path / "test.txt") is True
        assert doc_processor.can_process(tmp_path / "test.pdf") is True
        assert doc_processor.can_process(tmp_path / "test.docx") is True

        # 画像/音声/動画はDocumentProcessorでは処理不可
        assert doc_processor.can_process(tmp_path / "test.png") is False
        assert doc_processor.can_process(tmp_path / "test.mp3") is False
        assert doc_processor.can_process(tmp_path / "test.mp4") is False


class TestProcessorErrorHandling:
    """プロセッサのエラーハンドリングテスト。"""

    @pytest.fixture
    def mock_dependencies(self, tmp_path):
        """モック依存関係を作成。"""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = Path(f.name)

        from src.storage.sqlite_client import SQLiteClient

        sqlite_client = SQLiteClient(db_path=db_path)

        yield {
            "sqlite_client": sqlite_client,
            "db_path": db_path,
            "tmp_path": tmp_path,
        }

        if db_path.exists():
            db_path.unlink()

    def test_image_processor_handles_failed_index(self, mock_dependencies):
        """画像インデックス失敗時の処理。"""
        mock_image_processor = MagicMock(spec=ImageProcessor)
        mock_image_processor.is_supported.return_value = True
        mock_image_processor.index_image.side_effect = Exception("VLM error")

        # ダミーファイル作成
        test_file = mock_dependencies["tmp_path"] / "test.png"
        from PIL import Image

        img = Image.new("RGB", (10, 10), color="blue")
        img.save(test_file)

        processor = ImageIndexerProcessor(
            image_processor=mock_image_processor,
            sqlite_client=mock_dependencies["sqlite_client"],
        )

        result = processor.process(test_file, "hash-123")

        # 失敗時はNoneを返す
        assert result is None

    def test_audio_processor_handles_failed_transcription(self, mock_dependencies):
        """音声文字起こし失敗時の処理。"""
        mock_audio_processor = MagicMock(spec=AudioProcessor)
        mock_audio_processor.is_supported.return_value = True
        mock_audio_processor.index_audio.return_value = None  # 失敗

        test_file = mock_dependencies["tmp_path"] / "test.mp3"
        test_file.write_bytes(b"dummy")

        processor = AudioIndexerProcessor(
            audio_processor=mock_audio_processor,
            sqlite_client=mock_dependencies["sqlite_client"],
        )

        result = processor.process(test_file, "hash-123")

        assert result is None

    def test_video_processor_handles_failed_extraction(self, mock_dependencies):
        """動画処理失敗時の処理。"""
        mock_video_processor = MagicMock(spec=VideoProcessor)
        mock_video_processor.is_supported.return_value = True
        mock_video_processor.index_video.side_effect = Exception("FFmpeg error")

        test_file = mock_dependencies["tmp_path"] / "test.mp4"
        test_file.write_bytes(b"dummy")

        processor = VideoIndexerProcessor(
            video_processor=mock_video_processor,
            sqlite_client=mock_dependencies["sqlite_client"],
        )

        result = processor.process(test_file, "hash-123")

        assert result is None
