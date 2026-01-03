"""hash_utilsのテスト。"""

import tempfile
from pathlib import Path

import pytest

from src.indexer.hash_utils import calculate_file_hash, quick_hash, text_hash


class TestCalculateFileHash:
    """calculate_file_hash関数のテスト。"""

    def test_compute_hash_for_small_file(self, tmp_path: Path):
        """小さいファイルのハッシュを計算できる。"""
        file_path = tmp_path / "small.txt"
        file_path.write_text("Hello, World!")

        result = calculate_file_hash(file_path)

        assert result is not None
        assert len(result) == 64  # SHA-256は64文字の16進数
        assert result.isalnum()

    def test_compute_hash_for_large_file(self, tmp_path: Path):
        """大きいファイルのハッシュを計算できる。"""
        file_path = tmp_path / "large.txt"
        # 200KBのファイル（chunk_sizeの2倍以上）
        content = "x" * (65536 * 3)
        file_path.write_text(content)

        result = calculate_file_hash(file_path)

        assert result is not None
        assert len(result) == 64

    def test_same_content_same_hash(self, tmp_path: Path):
        """同じ内容のファイルは同じハッシュを返す。"""
        content = "Test content for hashing"

        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text(content)
        file2.write_text(content)

        hash1 = calculate_file_hash(file1)
        hash2 = calculate_file_hash(file2)

        assert hash1 == hash2

    def test_different_content_different_hash(self, tmp_path: Path):
        """異なる内容のファイルは異なるハッシュを返す。"""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("Content A")
        file2.write_text("Content B")

        hash1 = calculate_file_hash(file1)
        hash2 = calculate_file_hash(file2)

        assert hash1 != hash2

    def test_same_file_returns_consistent_hash(self, tmp_path: Path):
        """同じファイルを複数回ハッシュしても同じ結果。"""
        file_path = tmp_path / "test.txt"
        file_path.write_text("Consistent content")

        hash1 = calculate_file_hash(file_path)
        hash2 = calculate_file_hash(file_path)
        hash3 = calculate_file_hash(file_path)

        assert hash1 == hash2 == hash3

    def test_accepts_string_path(self, tmp_path: Path):
        """文字列パスを受け入れる。"""
        file_path = tmp_path / "string_path.txt"
        file_path.write_text("Test")

        result = calculate_file_hash(str(file_path))

        assert result is not None
        assert len(result) == 64

    def test_nonexistent_file_raises_error(self, tmp_path: Path):
        """存在しないファイルでエラーを発生させる。"""
        nonexistent = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            calculate_file_hash(nonexistent)

    def test_empty_file(self, tmp_path: Path):
        """空ファイルのハッシュを計算できる。"""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")

        result = calculate_file_hash(empty_file)

        assert result is not None
        assert len(result) == 64

    def test_binary_file(self, tmp_path: Path):
        """バイナリファイルのハッシュを計算できる。"""
        binary_file = tmp_path / "binary.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe\xfd")

        result = calculate_file_hash(binary_file)

        assert result is not None
        assert len(result) == 64

    def test_unicode_content(self, tmp_path: Path):
        """Unicodeコンテンツを含むファイル。"""
        file_path = tmp_path / "unicode.txt"
        file_path.write_text("日本語テキスト 🎉 Émoji")

        result = calculate_file_hash(file_path)

        assert result is not None
        assert len(result) == 64

    def test_custom_chunk_size(self, tmp_path: Path):
        """カスタムチャンクサイズでハッシュを計算できる。"""
        file_path = tmp_path / "custom_chunk.txt"
        file_path.write_text("Custom chunk size test")

        result = calculate_file_hash(file_path, chunk_size=1024)

        assert result is not None
        assert len(result) == 64


class TestQuickHash:
    """quick_hash関数のテスト。"""

    def test_hash_bytes(self):
        """バイト列のハッシュを計算できる。"""
        content = b"Hello, World!"

        result = quick_hash(content)

        assert result is not None
        assert len(result) == 64

    def test_same_content_same_hash(self):
        """同じ内容は同じハッシュを返す。"""
        content = b"Test content"

        hash1 = quick_hash(content)
        hash2 = quick_hash(content)

        assert hash1 == hash2

    def test_different_content_different_hash(self):
        """異なる内容は異なるハッシュを返す。"""
        hash1 = quick_hash(b"Content A")
        hash2 = quick_hash(b"Content B")

        assert hash1 != hash2

    def test_empty_bytes(self):
        """空のバイト列のハッシュを計算できる。"""
        result = quick_hash(b"")

        assert result is not None
        assert len(result) == 64


class TestTextHash:
    """text_hash関数のテスト。"""

    def test_hash_text(self):
        """テキストのハッシュを計算できる。"""
        text = "Hello, World!"

        result = text_hash(text)

        assert result is not None
        assert len(result) == 64

    def test_same_text_same_hash(self):
        """同じテキストは同じハッシュを返す。"""
        text = "Test content"

        hash1 = text_hash(text)
        hash2 = text_hash(text)

        assert hash1 == hash2

    def test_different_text_different_hash(self):
        """異なるテキストは異なるハッシュを返す。"""
        hash1 = text_hash("Text A")
        hash2 = text_hash("Text B")

        assert hash1 != hash2

    def test_empty_text(self):
        """空のテキストのハッシュを計算できる。"""
        result = text_hash("")

        assert result is not None
        assert len(result) == 64

    def test_unicode_text(self):
        """Unicodeテキストのハッシュを計算できる。"""
        result = text_hash("日本語テキスト 🎉")

        assert result is not None
        assert len(result) == 64

    def test_text_hash_matches_quick_hash(self):
        """text_hashはquick_hashのUTF-8エンコード版と一致する。"""
        text = "Hello, World!"

        text_result = text_hash(text)
        quick_result = quick_hash(text.encode("utf-8"))

        assert text_result == quick_result
