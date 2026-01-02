"""HybridSearchのテスト。"""

from unittest.mock import MagicMock, patch

import pytest

from src.search.hybrid_search import HybridSearch, HybridSearchResult


@pytest.fixture
def mock_vector_results():
    """モックベクトル検索結果。"""
    mock = MagicMock()
    mock.chunk_id = "chunk-v1"
    mock.document_id = "doc-v1"
    mock.text = "Vector search result text"
    mock.path = "/test/vector.txt"
    mock.filename = "vector.txt"
    mock.media_type = "document"
    mock.score = 0.9
    mock.start_time = None
    mock.end_time = None
    return [mock]


@pytest.fixture
def mock_bm25_results():
    """モックBM25検索結果。"""
    mock = MagicMock()
    mock.chunk_id = "chunk-b1"
    mock.document_id = "doc-b1"
    mock.text = "BM25 search result text"
    mock.path = "/test/bm25.txt"
    mock.filename = "bm25.txt"
    mock.bm25_score = 0.8
    return [mock]


def test_hybrid_search_result_dataclass():
    """HybridSearchResultのデータクラス。"""
    result = HybridSearchResult(
        chunk_id="chunk-1",
        document_id="doc-1",
        text="Test text",
        path="/test/path.txt",
        filename="path.txt",
        media_type="document",
        score=0.85,
        vector_score=0.9,
        bm25_score=0.8,
    )
    assert result.chunk_id == "chunk-1"
    assert result.score == 0.85


@patch("src.search.hybrid_search.VectorSearch")
@patch("src.search.hybrid_search.BM25Search")
def test_hybrid_search_combines_results(
    mock_bm25_class, mock_vector_class, mock_vector_results, mock_bm25_results
):
    """ハイブリッド検索が結果を統合する。"""
    mock_vector_instance = MagicMock()
    mock_vector_instance.search.return_value = mock_vector_results
    mock_vector_class.return_value = mock_vector_instance

    mock_bm25_instance = MagicMock()
    mock_bm25_instance.search.return_value = mock_bm25_results
    mock_bm25_class.return_value = mock_bm25_instance

    search = HybridSearch()
    results = search.search("test query", limit=10)

    assert len(results) >= 1
    assert all(isinstance(r, HybridSearchResult) for r in results)
    mock_vector_instance.search.assert_called_once()
    mock_bm25_instance.search.assert_called_once()


@patch("src.search.hybrid_search.VectorSearch")
@patch("src.search.hybrid_search.BM25Search")
def test_hybrid_search_handles_empty_results(mock_bm25_class, mock_vector_class):
    """空の結果を処理する。"""
    mock_vector_instance = MagicMock()
    mock_vector_instance.search.return_value = []
    mock_vector_class.return_value = mock_vector_instance

    mock_bm25_instance = MagicMock()
    mock_bm25_instance.search.return_value = []
    mock_bm25_class.return_value = mock_bm25_instance

    search = HybridSearch()
    results = search.search("nonexistent", limit=10)

    assert results == []


def test_to_dict():
    """to_dictメソッド。"""
    results = [
        HybridSearchResult(
            chunk_id="chunk-1",
            document_id="doc-1",
            text="Test text",
            path="/test/path.txt",
            filename="path.txt",
            media_type="document",
            score=0.85,
            vector_score=0.9,
            bm25_score=0.8,
            start_time=1.0,
            end_time=5.0,
        )
    ]
    search = HybridSearch.__new__(HybridSearch)
    dicts = search.to_dict(results)

    assert len(dicts) == 1
    assert dicts[0]["chunk_id"] == "chunk-1"
    assert dicts[0]["start_time"] == 1.0
