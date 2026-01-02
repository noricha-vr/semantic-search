"""SQLiteClientのテスト。"""

import tempfile
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


def test_init_creates_tables(client, temp_db):
    """初期化でテーブルが作成される。"""
    assert temp_db.exists()


def test_add_and_get_document(client):
    """ドキュメントの追加と取得。"""
    from datetime import datetime

    doc = {
        "id": "test-doc-1",
        "content_hash": "abc123",
        "path": "/test/path.txt",
        "filename": "path.txt",
        "extension": ".txt",
        "media_type": "document",
        "size": 100,
        "created_at": datetime.now(),
        "modified_at": datetime.now(),
        "indexed_at": datetime.now(),
    }
    client.add_document(doc)

    result = client.get_document_by_id("test-doc-1")
    assert result is not None
    assert result["path"] == "/test/path.txt"
    assert result["filename"] == "path.txt"


def test_get_document_by_path(client):
    """パスでドキュメントを取得。"""
    from datetime import datetime

    doc = {
        "id": "test-doc-2",
        "content_hash": "def456",
        "path": "/unique/path.txt",
        "filename": "path.txt",
        "extension": ".txt",
        "media_type": "document",
        "size": 200,
        "created_at": datetime.now(),
        "modified_at": datetime.now(),
        "indexed_at": datetime.now(),
    }
    client.add_document(doc)

    result = client.get_document_by_path("/unique/path.txt")
    assert result is not None
    assert result["id"] == "test-doc-2"


def test_add_chunks_and_search_fts(client):
    """チャンクの追加とFTS検索。"""
    chunks = [
        {
            "id": "chunk-1",
            "document_id": "doc-1",
            "text": "This is a test document about Python programming",
            "path": "/test/python.txt",
            "filename": "python.txt",
        },
        {
            "id": "chunk-2",
            "document_id": "doc-2",
            "text": "Another document about JavaScript development",
            "path": "/test/javascript.txt",
            "filename": "javascript.txt",
        },
    ]
    client.add_chunks_fts(chunks)

    results = client.search_fts("Python", limit=10)
    assert len(results) >= 1
    assert results[0]["chunk_id"] == "chunk-1"
    assert "Python" in results[0]["text"]


def test_search_fts_returns_empty_for_no_match(client):
    """マッチしない検索はから結果を返す。"""
    results = client.search_fts("nonexistent_term_xyz", limit=10)
    assert len(results) == 0


def test_delete_document_soft(client):
    """ソフト削除。"""
    from datetime import datetime

    doc = {
        "id": "test-doc-delete",
        "content_hash": "xyz789",
        "path": "/delete/test.txt",
        "filename": "test.txt",
        "extension": ".txt",
        "media_type": "document",
        "size": 50,
        "created_at": datetime.now(),
        "modified_at": datetime.now(),
        "indexed_at": datetime.now(),
    }
    client.add_document(doc)
    client.delete_document("test-doc-delete", hard_delete=False)

    result = client.get_document_by_id("test-doc-delete")
    assert result is not None
    assert result["is_deleted"] == 1


def test_get_stats(client):
    """統計情報の取得。"""
    from datetime import datetime

    doc = {
        "id": "stats-doc",
        "content_hash": "stats123",
        "path": "/stats/test.txt",
        "filename": "test.txt",
        "extension": ".txt",
        "media_type": "document",
        "size": 100,
        "created_at": datetime.now(),
        "modified_at": datetime.now(),
        "indexed_at": datetime.now(),
    }
    client.add_document(doc)

    stats = client.get_stats()
    assert stats["total_documents"] >= 1
    assert "by_media_type" in stats
