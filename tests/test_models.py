"""Pydantic models tests."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.storage.models import (
    ChunkRecord,
    DocumentRecord,
    DocumentStats,
    IndexedDirectory,
    SearchChunkResult,
    TranscriptRecord,
)


class TestDocumentRecord:
    """DocumentRecordのテスト。"""

    def test_create_with_required_fields(self):
        """必須フィールドでの作成。"""
        now = datetime.now(timezone.utc)
        record = DocumentRecord(
            id="test-id",
            content_hash="abc123",
            path="/path/to/file.pdf",
            filename="file.pdf",
            extension=".pdf",
            media_type="document",
            size=1024,
            created_at=now,
            modified_at=now,
            indexed_at=now,
        )
        assert record.id == "test-id"
        assert record.content_hash == "abc123"
        assert record.is_deleted is False
        assert record.deleted_at is None
        assert record.duration_seconds is None
        assert record.width is None
        assert record.height is None

    def test_create_with_all_fields(self):
        """全フィールドでの作成。"""
        now = datetime.now(timezone.utc)
        record = DocumentRecord(
            id="test-id",
            content_hash="abc123",
            path="/path/to/video.mp4",
            filename="video.mp4",
            extension=".mp4",
            media_type="video",
            size=1024000,
            created_at=now,
            modified_at=now,
            indexed_at=now,
            is_deleted=False,
            deleted_at=None,
            duration_seconds=120.5,
            width=1920,
            height=1080,
        )
        assert record.duration_seconds == 120.5
        assert record.width == 1920
        assert record.height == 1080

    def test_model_dump(self):
        """model_dumpで辞書に変換。"""
        now = datetime.now(timezone.utc)
        record = DocumentRecord(
            id="test-id",
            content_hash="abc123",
            path="/path/to/file.pdf",
            filename="file.pdf",
            extension=".pdf",
            media_type="document",
            size=1024,
            created_at=now,
            modified_at=now,
            indexed_at=now,
        )
        data = record.model_dump()
        assert isinstance(data, dict)
        assert data["id"] == "test-id"
        assert data["is_deleted"] is False

    def test_missing_required_field_raises_error(self):
        """必須フィールドがない場合はエラー。"""
        with pytest.raises(ValidationError):
            DocumentRecord(
                id="test-id",
                content_hash="abc123",
                # path is missing
            )


class TestChunkRecord:
    """ChunkRecordのテスト。"""

    def test_create_chunk(self):
        """チャンクレコードの作成。"""
        chunk = ChunkRecord(
            id="chunk-1",
            document_id="doc-1",
            text="This is sample text.",
            path="/path/to/file.pdf",
            filename="file.pdf",
        )
        assert chunk.id == "chunk-1"
        assert chunk.document_id == "doc-1"
        assert chunk.text == "This is sample text."


class TestTranscriptRecord:
    """TranscriptRecordのテスト。"""

    def test_create_transcript(self):
        """トランスクリプトレコードの作成。"""
        transcript = TranscriptRecord(
            id="transcript-1",
            document_id="doc-1",
            full_text="Hello world",
            language="en",
            duration_seconds=30.5,
            word_count=2,
        )
        assert transcript.id == "transcript-1"
        assert transcript.language == "en"
        assert transcript.duration_seconds == 30.5
        assert transcript.word_count == 2


class TestDocumentStats:
    """DocumentStatsのテスト。"""

    def test_create_stats(self):
        """統計情報の作成。"""
        stats = DocumentStats(
            total_documents=100,
            by_media_type={"document": 50, "image": 30, "audio": 20},
            total_chunks=500,
            last_indexed_at="2024-01-01T00:00:00",
        )
        assert stats.total_documents == 100
        assert stats.by_media_type["document"] == 50
        assert stats.total_chunks == 500

    def test_create_stats_without_last_indexed(self):
        """last_indexed_atなしでの統計情報作成。"""
        stats = DocumentStats(
            total_documents=0,
            by_media_type={},
            total_chunks=0,
        )
        assert stats.last_indexed_at is None


class TestIndexedDirectory:
    """IndexedDirectoryのテスト。"""

    def test_create_indexed_directory(self):
        """インデックス済みディレクトリの作成。"""
        directory = IndexedDirectory(
            path="/Users/test/documents",
            file_count=42,
        )
        assert directory.path == "/Users/test/documents"
        assert directory.file_count == 42


class TestSearchChunkResult:
    """SearchChunkResultのテスト。"""

    def test_create_search_result(self):
        """検索結果の作成。"""
        result = SearchChunkResult(
            chunk_id="chunk-1",
            document_id="doc-1",
            text="Matching text content",
            path="/path/to/file.pdf",
            filename="file.pdf",
            bm25_score=1.5,
        )
        assert result.chunk_id == "chunk-1"
        assert result.bm25_score == 1.5

    def test_negative_score_raises_error(self):
        """負のスコアはエラー。"""
        with pytest.raises(ValidationError):
            SearchChunkResult(
                chunk_id="chunk-1",
                document_id="doc-1",
                text="text",
                path="/path",
                filename="file.pdf",
                bm25_score=-1.0,
            )
