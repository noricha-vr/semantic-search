"""リポジトリ統合テスト。

DocumentRepository、ChunkRepository、TranscriptRepositoryの連携をテストする。
"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.storage.sqlite_client import SQLiteClient


@pytest.fixture
def temp_db():
    """一時データベースを作成。"""
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def client(temp_db):
    """SQLiteClientを作成。"""
    return SQLiteClient(db_path=temp_db)


class TestDocumentChunkIntegration:
    """ドキュメントとチャンクの連携テスト。"""

    def test_add_document_then_add_chunks(self, client):
        """ドキュメント追加後にチャンクを追加できる。"""
        now = datetime.now(timezone.utc)
        doc = {
            "id": "doc-1",
            "content_hash": "hash123",
            "path": "/test/document.txt",
            "filename": "document.txt",
            "extension": ".txt",
            "media_type": "document",
            "size": 1000,
            "created_at": now,
            "modified_at": now,
            "indexed_at": now,
        }
        client.add_document(doc)

        chunks = [
            {
                "id": "chunk-1",
                "document_id": "doc-1",
                "text": "First chunk of the document about Python programming",
                "path": "/test/document.txt",
                "filename": "document.txt",
            },
            {
                "id": "chunk-2",
                "document_id": "doc-1",
                "text": "Second chunk about machine learning and AI",
                "path": "/test/document.txt",
                "filename": "document.txt",
            },
        ]
        client.add_chunks_fts(chunks)

        # ドキュメントが存在する
        doc_result = client.get_document_by_id("doc-1")
        assert doc_result is not None
        assert doc_result["path"] == "/test/document.txt"

        # チャンクが検索可能
        results = client.search_fts("Python", limit=10)
        assert len(results) == 1
        assert results[0]["document_id"] == "doc-1"

        results = client.search_fts("machine learning", limit=10)
        assert len(results) == 1
        assert results[0]["chunk_id"] == "chunk-2"

    def test_add_multiple_documents_with_chunks(self, client):
        """複数ドキュメントにそれぞれチャンクを追加。"""
        now = datetime.now(timezone.utc)

        for i in range(3):
            doc = {
                "id": f"doc-{i}",
                "content_hash": f"hash-{i}",
                "path": f"/test/doc{i}.txt",
                "filename": f"doc{i}.txt",
                "extension": ".txt",
                "media_type": "document",
                "size": 100 * (i + 1),
                "created_at": now,
                "modified_at": now,
                "indexed_at": now,
            }
            client.add_document(doc)

            chunks = [
                {
                    "id": f"chunk-{i}-0",
                    "document_id": f"doc-{i}",
                    "text": f"Document {i} first chunk unique content",
                    "path": f"/test/doc{i}.txt",
                    "filename": f"doc{i}.txt",
                },
            ]
            client.add_chunks_fts(chunks)

        # 統計情報で確認
        stats = client.get_stats()
        assert stats["total_documents"] == 3
        assert stats["total_chunks"] == 3

    def test_search_across_documents(self, client):
        """複数ドキュメントを横断検索。"""
        now = datetime.now(timezone.utc)

        # ドキュメント1: Python関連
        doc1 = {
            "id": "doc-python",
            "content_hash": "hash-python",
            "path": "/test/python.txt",
            "filename": "python.txt",
            "extension": ".txt",
            "media_type": "document",
            "size": 500,
            "created_at": now,
            "modified_at": now,
            "indexed_at": now,
        }
        client.add_document(doc1)
        client.add_chunks_fts([
            {
                "id": "chunk-py-1",
                "document_id": "doc-python",
                "text": "Python programming language is great for data science",
                "path": "/test/python.txt",
                "filename": "python.txt",
            },
        ])

        # ドキュメント2: JavaScript関連
        doc2 = {
            "id": "doc-js",
            "content_hash": "hash-js",
            "path": "/test/javascript.txt",
            "filename": "javascript.txt",
            "extension": ".txt",
            "media_type": "document",
            "size": 600,
            "created_at": now,
            "modified_at": now,
            "indexed_at": now,
        }
        client.add_document(doc2)
        client.add_chunks_fts([
            {
                "id": "chunk-js-1",
                "document_id": "doc-js",
                "text": "JavaScript is essential for web development",
                "path": "/test/javascript.txt",
                "filename": "javascript.txt",
            },
        ])

        # ドキュメント3: 両方に言及
        doc3 = {
            "id": "doc-both",
            "content_hash": "hash-both",
            "path": "/test/fullstack.txt",
            "filename": "fullstack.txt",
            "extension": ".txt",
            "media_type": "document",
            "size": 700,
            "created_at": now,
            "modified_at": now,
            "indexed_at": now,
        }
        client.add_document(doc3)
        client.add_chunks_fts([
            {
                "id": "chunk-both-1",
                "document_id": "doc-both",
                "text": "Full stack development with Python backend and JavaScript frontend",
                "path": "/test/fullstack.txt",
                "filename": "fullstack.txt",
            },
        ])

        # Python検索：2件ヒット
        results = client.search_fts("Python", limit=10)
        assert len(results) == 2
        doc_ids = {r["document_id"] for r in results}
        assert "doc-python" in doc_ids
        assert "doc-both" in doc_ids

        # JavaScript検索：2件ヒット
        results = client.search_fts("JavaScript", limit=10)
        assert len(results) == 2
        doc_ids = {r["document_id"] for r in results}
        assert "doc-js" in doc_ids
        assert "doc-both" in doc_ids


class TestDocumentTranscriptIntegration:
    """ドキュメントとトランスクリプトの連携テスト。"""

    def test_add_document_with_transcript(self, client):
        """ドキュメントにトランスクリプトを関連付け。"""
        now = datetime.now(timezone.utc)

        # 音声ドキュメント
        doc = {
            "id": "audio-doc-1",
            "content_hash": "audio-hash-1",
            "path": "/test/podcast.mp3",
            "filename": "podcast.mp3",
            "extension": ".mp3",
            "media_type": "audio",
            "size": 5000000,
            "created_at": now,
            "modified_at": now,
            "indexed_at": now,
            "duration_seconds": 3600.0,
        }
        client.add_document(doc)

        # トランスクリプト
        transcript = {
            "id": "transcript-1",
            "document_id": "audio-doc-1",
            "full_text": "Welcome to our podcast about technology and innovation.",
            "language": "en",
            "duration_seconds": 3600.0,
            "word_count": 8,
        }
        client.add_transcript(transcript)

        # 取得確認
        doc_result = client.get_document_by_id("audio-doc-1")
        assert doc_result is not None
        assert doc_result["media_type"] == "audio"

        transcript_result = client.get_transcript("audio-doc-1")
        assert transcript_result is not None
        assert "technology" in transcript_result["full_text"]
        assert transcript_result["language"] == "en"

    def test_video_with_transcript_and_dimensions(self, client):
        """動画ドキュメントにトランスクリプトとサイズ情報を関連付け。"""
        now = datetime.now(timezone.utc)

        # 動画ドキュメント
        doc = {
            "id": "video-doc-1",
            "content_hash": "video-hash-1",
            "path": "/test/tutorial.mp4",
            "filename": "tutorial.mp4",
            "extension": ".mp4",
            "media_type": "video",
            "size": 50000000,
            "created_at": now,
            "modified_at": now,
            "indexed_at": now,
            "duration_seconds": 1800.0,
            "width": 1920,
            "height": 1080,
        }
        client.add_document(doc)

        # トランスクリプト
        transcript = {
            "id": "transcript-video-1",
            "document_id": "video-doc-1",
            "full_text": "In this tutorial we will learn about machine learning basics.",
            "language": "en",
            "duration_seconds": 1800.0,
            "word_count": 10,
        }
        client.add_transcript(transcript)

        # 取得確認
        doc_result = client.get_document_by_id("video-doc-1")
        assert doc_result is not None
        assert doc_result["width"] == 1920
        assert doc_result["height"] == 1080
        assert doc_result["duration_seconds"] == 1800.0

        transcript_result = client.get_transcript("video-doc-1")
        assert transcript_result is not None
        assert "machine learning" in transcript_result["full_text"]


class TestCascadeDeleteIntegration:
    """削除時のカスケード動作テスト。"""

    def test_delete_document_deletes_chunks(self, client):
        """ドキュメント削除でチャンクも削除される。"""
        now = datetime.now(timezone.utc)

        doc = {
            "id": "doc-to-delete",
            "content_hash": "delete-hash",
            "path": "/test/delete-me.txt",
            "filename": "delete-me.txt",
            "extension": ".txt",
            "media_type": "document",
            "size": 200,
            "created_at": now,
            "modified_at": now,
            "indexed_at": now,
        }
        client.add_document(doc)

        chunks = [
            {
                "id": "chunk-del-1",
                "document_id": "doc-to-delete",
                "text": "Content to be deleted permanently",
                "path": "/test/delete-me.txt",
                "filename": "delete-me.txt",
            },
            {
                "id": "chunk-del-2",
                "document_id": "doc-to-delete",
                "text": "More content also deleted",
                "path": "/test/delete-me.txt",
                "filename": "delete-me.txt",
            },
        ]
        client.add_chunks_fts(chunks)

        # 削除前：検索可能
        results = client.search_fts("deleted", limit=10)
        assert len(results) >= 1

        # 物理削除
        client.delete_document("doc-to-delete", hard_delete=True)

        # 削除後：ドキュメントなし
        doc_result = client.get_document_by_id("doc-to-delete")
        assert doc_result is None

        # 削除後：チャンクも検索不可
        results = client.search_fts("deleted", limit=10)
        assert len(results) == 0

    def test_delete_document_deletes_transcript(self, client):
        """ドキュメント削除でトランスクリプトも削除される。"""
        now = datetime.now(timezone.utc)

        doc = {
            "id": "audio-to-delete",
            "content_hash": "audio-delete-hash",
            "path": "/test/delete-audio.mp3",
            "filename": "delete-audio.mp3",
            "extension": ".mp3",
            "media_type": "audio",
            "size": 1000000,
            "created_at": now,
            "modified_at": now,
            "indexed_at": now,
            "duration_seconds": 120.0,
        }
        client.add_document(doc)

        transcript = {
            "id": "transcript-to-delete",
            "document_id": "audio-to-delete",
            "full_text": "Audio content transcript",
            "language": "en",
            "duration_seconds": 120.0,
            "word_count": 3,
        }
        client.add_transcript(transcript)

        # 削除前：トランスクリプトあり
        transcript_result = client.get_transcript("audio-to-delete")
        assert transcript_result is not None

        # 物理削除
        client.delete_document("audio-to-delete", hard_delete=True)

        # 削除後：トランスクリプトもなし
        transcript_result = client.get_transcript("audio-to-delete")
        assert transcript_result is None

    def test_soft_delete_keeps_data(self, client):
        """ソフト削除ではデータは保持される。"""
        now = datetime.now(timezone.utc)

        doc = {
            "id": "doc-soft-delete",
            "content_hash": "soft-delete-hash",
            "path": "/test/soft-delete.txt",
            "filename": "soft-delete.txt",
            "extension": ".txt",
            "media_type": "document",
            "size": 300,
            "created_at": now,
            "modified_at": now,
            "indexed_at": now,
        }
        client.add_document(doc)

        chunks = [
            {
                "id": "chunk-soft-1",
                "document_id": "doc-soft-delete",
                "text": "Soft deleted content remains searchable",
                "path": "/test/soft-delete.txt",
                "filename": "soft-delete.txt",
            },
        ]
        client.add_chunks_fts(chunks)

        # ソフト削除
        client.delete_document("doc-soft-delete", hard_delete=False)

        # ドキュメントは存在するがis_deleted=1
        doc_result = client.get_document_by_id("doc-soft-delete")
        assert doc_result is not None
        assert doc_result["is_deleted"] == 1
        assert doc_result["deleted_at"] is not None

        # チャンクは検索可能（FTSテーブルは影響なし）
        results = client.search_fts("searchable", limit=10)
        assert len(results) == 1


class TestFullWorkflowIntegration:
    """完全なワークフローの統合テスト。"""

    def test_index_search_delete_workflow(self, client):
        """インデックス→検索→削除の一連のフロー。"""
        now = datetime.now(timezone.utc)

        # Step 1: ドキュメントをインデックス
        doc = {
            "id": "workflow-doc",
            "content_hash": "workflow-hash",
            "path": "/test/workflow.txt",
            "filename": "workflow.txt",
            "extension": ".txt",
            "media_type": "document",
            "size": 500,
            "created_at": now,
            "modified_at": now,
            "indexed_at": now,
        }
        client.add_document(doc)

        chunks = [
            {
                "id": "workflow-chunk-1",
                "document_id": "workflow-doc",
                "text": "This document covers integration testing strategies",
                "path": "/test/workflow.txt",
                "filename": "workflow.txt",
            },
            {
                "id": "workflow-chunk-2",
                "document_id": "workflow-doc",
                "text": "Unit tests and integration tests work together",
                "path": "/test/workflow.txt",
                "filename": "workflow.txt",
            },
        ]
        client.add_chunks_fts(chunks)

        # Step 2: 統計確認
        stats = client.get_stats()
        assert stats["total_documents"] >= 1
        assert stats["total_chunks"] >= 2

        # Step 3: 検索
        results = client.search_fts("integration", limit=10)
        assert len(results) == 2

        results = client.search_fts("testing strategies", limit=10)
        assert len(results) >= 1

        # Step 4: パスで取得
        doc_result = client.get_document_by_path("/test/workflow.txt")
        assert doc_result is not None
        assert doc_result["id"] == "workflow-doc"

        # Step 5: ハッシュで取得
        doc_result = client.get_document_by_hash("workflow-hash")
        assert doc_result is not None
        assert doc_result["id"] == "workflow-doc"

        # Step 6: 削除
        client.delete_document("workflow-doc", hard_delete=True)

        # Step 7: 削除確認
        doc_result = client.get_document_by_id("workflow-doc")
        assert doc_result is None

        results = client.search_fts("integration", limit=10)
        # 他のテストで追加されたものがなければ0
        workflow_results = [r for r in results if r.get("document_id") == "workflow-doc"]
        assert len(workflow_results) == 0

    def test_mixed_media_types_workflow(self, client):
        """複数メディアタイプの混在ワークフロー。"""
        now = datetime.now(timezone.utc)

        # テキストドキュメント
        doc_text = {
            "id": "mixed-text",
            "content_hash": "text-hash",
            "path": "/test/readme.md",
            "filename": "readme.md",
            "extension": ".md",
            "media_type": "document",
            "size": 1000,
            "created_at": now,
            "modified_at": now,
            "indexed_at": now,
        }
        client.add_document(doc_text)
        client.add_chunks_fts([
            {
                "id": "chunk-text-1",
                "document_id": "mixed-text",
                "text": "Project documentation with setup instructions",
                "path": "/test/readme.md",
                "filename": "readme.md",
            },
        ])

        # 画像
        doc_image = {
            "id": "mixed-image",
            "content_hash": "image-hash",
            "path": "/test/screenshot.png",
            "filename": "screenshot.png",
            "extension": ".png",
            "media_type": "image",
            "size": 500000,
            "created_at": now,
            "modified_at": now,
            "indexed_at": now,
            "width": 1920,
            "height": 1080,
        }
        client.add_document(doc_image)

        # 音声
        doc_audio = {
            "id": "mixed-audio",
            "content_hash": "audio-hash",
            "path": "/test/recording.mp3",
            "filename": "recording.mp3",
            "extension": ".mp3",
            "media_type": "audio",
            "size": 2000000,
            "created_at": now,
            "modified_at": now,
            "indexed_at": now,
            "duration_seconds": 300.0,
        }
        client.add_document(doc_audio)
        client.add_transcript({
            "id": "transcript-audio",
            "document_id": "mixed-audio",
            "full_text": "Recording of meeting discussion",
            "language": "en",
            "duration_seconds": 300.0,
            "word_count": 4,
        })

        # 統計確認
        stats = client.get_stats()
        assert stats["total_documents"] >= 3
        assert "document" in stats["by_media_type"]
        assert "image" in stats["by_media_type"]
        assert "audio" in stats["by_media_type"]

        # 最近のドキュメント取得
        recent = client.get_recent_documents(limit=10)
        assert len(recent) >= 3

        # メディアタイプでフィルタ
        recent_images = client.get_recent_documents(limit=10, media_type="image")
        assert len(recent_images) >= 1
        assert all(d["media_type"] == "image" for d in recent_images)


class TestRepositoryDirectAccess:
    """リポジトリへの直接アクセステスト。"""

    def test_access_document_repository(self, client):
        """DocumentRepositoryへの直接アクセス。"""
        now = datetime.now(timezone.utc)

        doc = {
            "id": "direct-doc",
            "content_hash": "direct-hash",
            "path": "/test/direct.txt",
            "filename": "direct.txt",
            "extension": ".txt",
            "media_type": "document",
            "size": 100,
            "created_at": now,
            "modified_at": now,
            "indexed_at": now,
        }

        # リポジトリ経由で追加
        client.documents.add(doc)

        # リポジトリ経由で取得
        result = client.documents.get_by_id("direct-doc")
        assert result is not None
        assert result["path"] == "/test/direct.txt"

    def test_access_chunk_repository(self, client):
        """ChunkRepositoryへの直接アクセス。"""
        chunks = [
            {
                "id": "direct-chunk",
                "document_id": "doc-x",
                "text": "Direct repository access test content",
                "path": "/test/direct.txt",
                "filename": "direct.txt",
            },
        ]

        # リポジトリ経由で追加
        client.chunks.add_chunks(chunks)

        # リポジトリ経由で検索
        results = client.chunks.search("repository access", limit=10)
        assert len(results) >= 1

    def test_access_transcript_repository(self, client):
        """TranscriptRepositoryへの直接アクセス。"""
        now = datetime.now(timezone.utc)

        # ドキュメントを先に追加（外部キー制約のため）
        doc = {
            "id": "transcript-parent",
            "content_hash": "parent-hash",
            "path": "/test/parent.mp3",
            "filename": "parent.mp3",
            "extension": ".mp3",
            "media_type": "audio",
            "size": 100000,
            "created_at": now,
            "modified_at": now,
            "indexed_at": now,
        }
        client.add_document(doc)

        transcript = {
            "id": "direct-transcript",
            "document_id": "transcript-parent",
            "full_text": "Direct transcript repository test",
            "language": "en",
            "duration_seconds": 60.0,
            "word_count": 4,
        }

        # リポジトリ経由で追加
        client.transcripts.add(transcript)

        # リポジトリ経由で取得
        result = client.transcripts.get_by_document_id("transcript-parent")
        assert result is not None
        assert "Direct transcript" in result["full_text"]

        # リポジトリ経由で削除
        client.transcripts.delete_by_document_id("transcript-parent")
        result = client.transcripts.get_by_document_id("transcript-parent")
        assert result is None
