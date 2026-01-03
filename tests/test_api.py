"""APIエンドポイントのテスト。"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    """テストクライアント。"""
    return TestClient(app)


def test_health_endpoint(client):
    """ヘルスチェックエンドポイント。"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@patch("src.api.routes.search.HybridSearch")
def test_search_endpoint(mock_search_class, client):
    """検索エンドポイント。"""
    from src.search.hybrid_search import HybridSearchResult

    mock_instance = MagicMock()
    mock_instance.search.return_value = [
        HybridSearchResult(
            chunk_id="chunk-1",
            document_id="doc-1",
            text="Test result",
            path="/test/file.txt",
            filename="file.txt",
            media_type="document",
            score=0.9,
            vector_score=0.95,
            bm25_score=0.85,
        )
    ]
    mock_search_class.return_value = mock_instance

    response = client.get("/api/search?q=test")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "query" in data
    assert data["query"] == "test"


@patch("src.api.routes.search.HybridSearch")
def test_search_endpoint_empty_query(mock_search_class, client):
    """空のクエリ。"""
    mock_instance = MagicMock()
    mock_instance.search.return_value = []
    mock_search_class.return_value = mock_instance

    response = client.get("/api/search?q=")
    # 空クエリの処理は実装による
    assert response.status_code in [200, 400, 422]


@patch("src.api.routes.documents.SQLiteClient")
def test_documents_stats_endpoint(mock_sqlite_class, client):
    """統計エンドポイント。"""
    mock_instance = MagicMock()
    mock_instance.get_stats.return_value = {
        "total_documents": 10,
        "by_media_type": {"document": 5, "image": 3, "audio": 2},
        "total_chunks": 50,
        "last_indexed_at": "2024-01-01T00:00:00",
    }
    mock_sqlite_class.return_value = mock_instance

    response = client.get("/api/documents/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_documents" in data


def test_search_with_limit(client):
    """limit パラメータ付き検索。"""
    with patch("src.api.routes.search.HybridSearch") as mock_search_class:
        mock_instance = MagicMock()
        mock_instance.search.return_value = []
        mock_search_class.return_value = mock_instance

        response = client.get("/api/search?q=test&limit=5")
        assert response.status_code == 200
        mock_instance.search.assert_called_once()
        call_args = mock_instance.search.call_args
        assert call_args[1]["limit"] == 5


def test_search_with_media_type(client):
    """media_type パラメータ付き検索。"""
    with patch("src.api.routes.search.HybridSearch") as mock_search_class:
        mock_instance = MagicMock()
        mock_instance.search.return_value = []
        mock_search_class.return_value = mock_instance

        response = client.get("/api/search?q=test&media_type=image")
        assert response.status_code == 200


# 統合テスト
class TestAPIIntegration:
    """API統合テスト。"""

    @pytest.fixture
    def integration_client(self, tmp_path):
        """統合テスト用クライアント。"""
        import tempfile
        from pathlib import Path

        # 一時的なDB設定でテスト
        db_file = tmp_path / "test.sqlite"

        with patch("src.api.routes.documents.SQLiteClient") as mock_sqlite:
            mock_instance = MagicMock()
            mock_sqlite.return_value = mock_instance
            yield TestClient(app), mock_instance

    def test_full_document_workflow(self, client):
        """インデックス→検索→削除の一連フロー。"""
        from src.search.hybrid_search import HybridSearchResult

        # Step 1: 統計確認（初期状態）
        with patch("src.api.routes.documents.SQLiteClient") as mock_sqlite:
            mock_instance = MagicMock()
            mock_instance.get_stats.return_value = {
                "total_documents": 0,
                "by_media_type": {},
                "total_chunks": 0,
                "last_indexed_at": None,
            }
            mock_sqlite.return_value = mock_instance

            response = client.get("/api/documents/stats")
            assert response.status_code == 200
            data = response.json()
            assert data["total_documents"] == 0

        # Step 2: 検索（空の結果）
        with patch("src.api.routes.search.HybridSearch") as mock_search:
            mock_instance = MagicMock()
            mock_instance.search.return_value = []
            mock_search.return_value = mock_instance

            response = client.get("/api/search?q=test")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0

        # Step 3: ドキュメント追加後の検索
        with patch("src.api.routes.search.HybridSearch") as mock_search:
            mock_instance = MagicMock()
            mock_instance.search.return_value = [
                HybridSearchResult(
                    chunk_id="chunk-1",
                    document_id="doc-1",
                    text="Test document content about Python",
                    path="/test/python.txt",
                    filename="python.txt",
                    media_type="document",
                    score=0.85,
                    vector_score=0.9,
                    bm25_score=0.8,
                )
            ]
            mock_search.return_value = mock_instance

            response = client.get("/api/search?q=Python")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["results"][0]["text"] == "Test document content about Python"

        # Step 4: ドキュメント詳細取得
        with patch("src.api.routes.documents.SQLiteClient") as mock_sqlite:
            mock_instance = MagicMock()
            mock_instance.get_document_by_id.return_value = {
                "id": "doc-1",
                "path": "/test/python.txt",
                "filename": "python.txt",
                "extension": ".txt",
                "media_type": "document",
                "size": 1000,
                "created_at": "2024-01-01T00:00:00",
                "modified_at": "2024-01-01T00:00:00",
                "indexed_at": "2024-01-01T00:00:00",
            }
            mock_sqlite.return_value = mock_instance

            response = client.get("/api/documents/doc-1")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "doc-1"
            assert data["filename"] == "python.txt"

        # Step 5: ドキュメント削除
        with patch("src.api.routes.documents.SQLiteClient") as mock_sqlite, patch(
            "src.api.routes.documents.DocumentIndexer"
        ) as mock_indexer:
            mock_client = MagicMock()
            mock_client.get_document_by_id.return_value = {"id": "doc-1"}
            mock_sqlite.return_value = mock_client

            mock_indexer_instance = MagicMock()
            mock_indexer.return_value = mock_indexer_instance

            response = client.delete("/api/documents/doc-1")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "deleted"

    def test_document_not_found_returns_404(self, client):
        """存在しないドキュメントは404。"""
        with patch("src.api.routes.documents.SQLiteClient") as mock_sqlite:
            mock_instance = MagicMock()
            mock_instance.get_document_by_id.return_value = None
            mock_sqlite.return_value = mock_instance

            response = client.get("/api/documents/nonexistent-id")
            assert response.status_code == 404

    def test_transcript_endpoint(self, client):
        """Transcriptエンドポイント。"""
        with patch("src.api.routes.documents.SQLiteClient") as mock_sqlite:
            mock_instance = MagicMock()
            mock_instance.get_document_by_id.return_value = {
                "id": "audio-doc-1",
                "media_type": "audio",
            }
            mock_instance.get_transcript.return_value = {
                "id": "transcript-1",
                "document_id": "audio-doc-1",
                "full_text": "This is the audio transcript",
                "language": "en",
                "duration_seconds": 120.0,
                "word_count": 5,
            }
            mock_sqlite.return_value = mock_instance

            response = client.get("/api/documents/audio-doc-1/transcript")
            assert response.status_code == 200
            data = response.json()
            assert data["full_text"] == "This is the audio transcript"
            assert data["language"] == "en"

    def test_transcript_not_found_returns_null(self, client):
        """Transcriptがない場合はnull。"""
        with patch("src.api.routes.documents.SQLiteClient") as mock_sqlite:
            mock_instance = MagicMock()
            mock_instance.get_document_by_id.return_value = {"id": "doc-1"}
            mock_instance.get_transcript.return_value = None
            mock_sqlite.return_value = mock_instance

            response = client.get("/api/documents/doc-1/transcript")
            assert response.status_code == 200
            assert response.json() is None

    def test_list_documents(self, client):
        """ドキュメント一覧取得。"""
        with patch("src.api.routes.documents.SQLiteClient") as mock_sqlite:
            mock_instance = MagicMock()
            mock_instance.get_recent_documents.return_value = [
                {
                    "id": "doc-1",
                    "path": "/test/file1.txt",
                    "filename": "file1.txt",
                    "extension": ".txt",
                    "media_type": "document",
                    "size": 100,
                    "created_at": "2024-01-01T00:00:00",
                    "modified_at": "2024-01-01T00:00:00",
                    "indexed_at": "2024-01-01T00:00:00",
                },
                {
                    "id": "doc-2",
                    "path": "/test/file2.pdf",
                    "filename": "file2.pdf",
                    "extension": ".pdf",
                    "media_type": "document",
                    "size": 200,
                    "created_at": "2024-01-02T00:00:00",
                    "modified_at": "2024-01-02T00:00:00",
                    "indexed_at": "2024-01-02T00:00:00",
                },
            ]
            mock_instance.get_stats.return_value = {
                "total_documents": 2,
                "by_media_type": {"document": 2},
                "total_chunks": 10,
                "last_indexed_at": "2024-01-02T00:00:00",
            }
            mock_sqlite.return_value = mock_instance

            response = client.get("/api/documents?limit=10")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert len(data["documents"]) == 2

    def test_list_documents_with_media_filter(self, client):
        """メディアタイプフィルタ付きドキュメント一覧。"""
        with patch("src.api.routes.documents.SQLiteClient") as mock_sqlite:
            mock_instance = MagicMock()
            mock_instance.get_recent_documents.return_value = [
                {
                    "id": "img-1",
                    "path": "/test/photo.png",
                    "filename": "photo.png",
                    "extension": ".png",
                    "media_type": "image",
                    "size": 50000,
                    "created_at": "2024-01-01T00:00:00",
                    "modified_at": "2024-01-01T00:00:00",
                    "indexed_at": "2024-01-01T00:00:00",
                    "width": 800,
                    "height": 600,
                },
            ]
            mock_instance.get_stats.return_value = {
                "total_documents": 5,
                "by_media_type": {"document": 3, "image": 2},
                "total_chunks": 15,
                "last_indexed_at": "2024-01-01T00:00:00",
            }
            mock_sqlite.return_value = mock_instance

            response = client.get("/api/documents?media_type=image")
            assert response.status_code == 200
            data = response.json()
            assert all(d["media_type"] == "image" for d in data["documents"])

    def test_indexed_directories(self, client):
        """インデックス済みディレクトリ一覧。"""
        with patch("src.api.routes.documents.SQLiteClient") as mock_sqlite:
            mock_instance = MagicMock()
            mock_instance.get_indexed_directories.return_value = [
                {"path": "/Users/test/documents", "file_count": 50},
                {"path": "/Users/test/photos", "file_count": 30},
            ]
            mock_sqlite.return_value = mock_instance

            response = client.get("/api/documents/directories")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["file_count"] == 50


class TestSearchAPIIntegration:
    """検索API統合テスト。"""

    def test_search_returns_results_with_scores(self, client):
        """検索結果にスコアが含まれる。"""
        from src.search.hybrid_search import HybridSearchResult

        with patch("src.api.routes.search.HybridSearch") as mock_search:
            mock_instance = MagicMock()
            mock_instance.search.return_value = [
                HybridSearchResult(
                    chunk_id="chunk-1",
                    document_id="doc-1",
                    text="Result 1",
                    path="/test/file1.txt",
                    filename="file1.txt",
                    media_type="document",
                    score=0.95,
                    vector_score=0.97,
                    bm25_score=0.93,
                ),
                HybridSearchResult(
                    chunk_id="chunk-2",
                    document_id="doc-2",
                    text="Result 2",
                    path="/test/file2.txt",
                    filename="file2.txt",
                    media_type="document",
                    score=0.85,
                    vector_score=0.87,
                    bm25_score=0.83,
                ),
            ]
            mock_search.return_value = mock_instance

            response = client.get("/api/search?q=test")
            assert response.status_code == 200
            data = response.json()

            assert data["total"] == 2
            # スコア順にソートされている（高い順）
            assert data["results"][0]["score"] >= data["results"][1]["score"]

    def test_search_with_audio_result_includes_timestamps(self, client):
        """音声検索結果にタイムスタンプが含まれる。"""
        from src.search.hybrid_search import HybridSearchResult

        with patch("src.api.routes.search.HybridSearch") as mock_search:
            mock_instance = MagicMock()
            mock_instance.search.return_value = [
                HybridSearchResult(
                    chunk_id="chunk-audio-1",
                    document_id="doc-audio-1",
                    text="Audio segment text",
                    path="/test/podcast.mp3",
                    filename="podcast.mp3",
                    media_type="audio",
                    score=0.9,
                    vector_score=0.92,
                    bm25_score=0.88,
                    start_time=120.5,
                    end_time=150.0,
                ),
            ]
            mock_search.return_value = mock_instance

            response = client.get("/api/search?q=podcast")
            assert response.status_code == 200
            data = response.json()

            assert data["total"] == 1
            result = data["results"][0]
            assert result["media_type"] == "audio"
            assert result["start_time"] == 120.5
            assert result["end_time"] == 150.0

    def test_search_suggest_endpoint(self, client):
        """サジェストエンドポイント。"""
        response = client.get("/api/search/suggest?q=pyth")
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "pyth"
        assert "suggestions" in data

    def test_mixed_media_type_search(self, client):
        """複数メディアタイプの検索結果。"""
        from src.search.hybrid_search import HybridSearchResult

        with patch("src.api.routes.search.HybridSearch") as mock_search:
            mock_instance = MagicMock()
            mock_instance.search.return_value = [
                HybridSearchResult(
                    chunk_id="chunk-doc",
                    document_id="doc-1",
                    text="Document about machine learning",
                    path="/test/ml.pdf",
                    filename="ml.pdf",
                    media_type="document",
                    score=0.95,
                    vector_score=0.96,
                    bm25_score=0.94,
                ),
                HybridSearchResult(
                    chunk_id="chunk-img",
                    document_id="doc-img-1",
                    text="Image description: machine learning diagram",
                    path="/test/ml-diagram.png",
                    filename="ml-diagram.png",
                    media_type="image",
                    score=0.88,
                    vector_score=0.90,
                    bm25_score=0.86,
                ),
                HybridSearchResult(
                    chunk_id="chunk-audio",
                    document_id="doc-audio-1",
                    text="Podcast about machine learning basics",
                    path="/test/ml-podcast.mp3",
                    filename="ml-podcast.mp3",
                    media_type="audio",
                    score=0.82,
                    vector_score=0.84,
                    bm25_score=0.80,
                    start_time=0.0,
                    end_time=30.0,
                ),
            ]
            mock_search.return_value = mock_instance

            response = client.get("/api/search?q=machine%20learning")
            assert response.status_code == 200
            data = response.json()

            assert data["total"] == 3
            media_types = {r["media_type"] for r in data["results"]}
            assert "document" in media_types
            assert "image" in media_types
            assert "audio" in media_types


class TestErrorHandling:
    """エラーハンドリングテスト。"""

    def test_delete_nonexistent_document_returns_404(self, client):
        """存在しないドキュメント削除は404。"""
        with patch("src.api.routes.documents.SQLiteClient") as mock_sqlite:
            mock_instance = MagicMock()
            mock_instance.get_document_by_id.return_value = None
            mock_sqlite.return_value = mock_instance

            response = client.delete("/api/documents/nonexistent-id")
            assert response.status_code == 404

    def test_index_nonexistent_path_returns_404(self, client):
        """存在しないパスのインデックスは404。"""
        with patch("src.api.routes.documents.Path") as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = False
            mock_path.return_value.expanduser.return_value = mock_path_instance

            response = client.post(
                "/api/documents/index", json={"path": "/nonexistent/path"}
            )
            assert response.status_code == 404

    def test_transcript_for_nonexistent_document_returns_404(self, client):
        """存在しないドキュメントのTranscript取得は404。"""
        with patch("src.api.routes.documents.SQLiteClient") as mock_sqlite:
            mock_instance = MagicMock()
            mock_instance.get_document_by_id.return_value = None
            mock_sqlite.return_value = mock_instance

            response = client.get("/api/documents/nonexistent/transcript")
            assert response.status_code == 404
