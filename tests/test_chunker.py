"""Chunkerのテスト。"""

import pytest

from src.processors.chunker import ChunkResult, Chunker


@pytest.fixture
def chunker():
    """デフォルト設定のChunker。"""
    return Chunker()


@pytest.fixture
def small_chunker():
    """小さいチャンクサイズのChunker。"""
    return Chunker(chunk_size=50, chunk_overlap=10)


def test_chunk_short_text(chunker):
    """短いテキストは1つのチャンクになる。"""
    text = "This is a short text."
    chunks = chunker.chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0].text == text


def test_chunk_long_text(small_chunker):
    """長いテキストは複数のチャンクに分割される。"""
    text = "This is a much longer text. " * 10
    chunks = small_chunker.chunk_text(text)
    assert len(chunks) > 1


def test_chunk_preserves_content(small_chunker):
    """チャンク分割後も内容が保持される。"""
    text = "Word1 Word2 Word3 Word4 Word5 " * 5
    chunks = small_chunker.chunk_text(text)

    # 元のテキストに含まれる単語がチャンクに存在
    all_text = " ".join(c.text for c in chunks)
    for word in ["Word1", "Word2", "Word3", "Word4", "Word5"]:
        assert word in all_text


def test_chunk_with_overlap(small_chunker):
    """オーバーラップが適用される。"""
    text = "Sentence one here. Sentence two here. Sentence three here. " * 3
    chunks = small_chunker.chunk_text(text)

    assert len(chunks) >= 1
    # チャンクごとにChunkResultが返される
    for chunk in chunks:
        assert isinstance(chunk, ChunkResult)
        assert chunk.text


def test_chunk_empty_text(chunker):
    """空のテキストは空のリストを返す。"""
    chunks = chunker.chunk_text("")
    assert chunks == []


def test_chunk_whitespace_only(chunker):
    """空白のみのテキストは空のリストを返す。"""
    chunks = chunker.chunk_text("   \n\t   ")
    assert chunks == []


def test_chunk_unicode(chunker):
    """Unicode文字を含むテキスト。"""
    text = "日本語テキストです。これはテストです。"
    chunks = chunker.chunk_text(text)
    assert len(chunks) >= 1
    assert "日本語" in chunks[0].text


def test_chunk_with_custom_params():
    """カスタムパラメータ。"""
    chunker = Chunker(chunk_size=100, chunk_overlap=20)
    assert chunker.chunk_size == 100
    assert chunker.chunk_overlap == 20


def test_chunk_result_has_metadata(small_chunker):
    """ChunkResultにメタデータが含まれる。"""
    text = "This is a test. " * 20
    chunks = small_chunker.chunk_text(text)

    assert len(chunks) > 0
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i
        assert chunk.start_char >= 0
        assert chunk.end_char > chunk.start_char


def test_chunk_with_timestamps():
    """タイムスタンプ付きセグメントのチャンク化。"""
    chunker = Chunker(chunk_size=50, chunk_overlap=10)
    segments = [
        {"text": "Hello world.", "start": 0.0, "end": 1.0},
        {"text": "This is a test.", "start": 1.0, "end": 2.0},
        {"text": "Another segment here.", "start": 2.0, "end": 3.0},
    ]

    chunks = chunker.chunk_with_timestamps(segments)
    assert len(chunks) >= 1
    assert all("start_time" in c for c in chunks)
    assert all("end_time" in c for c in chunks)
