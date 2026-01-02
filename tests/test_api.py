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
