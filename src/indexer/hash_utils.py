"""ファイルハッシュ計算ユーティリティ。

ファイルの変更検出用にハッシュを計算する。
"""

import hashlib
from pathlib import Path


def calculate_file_hash(file_path: Path | str, chunk_size: int = 65536) -> str:
    """ファイルのハッシュを計算。

    先頭64KB + 末尾64KB + ファイルサイズでSHA-256を計算。
    大きなファイルでも高速に処理できる。

    Args:
        file_path: ファイルパス
        chunk_size: 読み込むチャンクサイズ（デフォルト64KB）

    Returns:
        SHA-256ハッシュ文字列
    """
    file_path = Path(file_path)
    file_size = file_path.stat().st_size

    hasher = hashlib.sha256()

    with open(file_path, "rb") as f:
        # 先頭を読み込み
        head = f.read(chunk_size)
        hasher.update(head)

        # ファイルサイズが2チャンク以上の場合、末尾も読み込み
        if file_size > chunk_size * 2:
            f.seek(-chunk_size, 2)  # 末尾から64KB
            tail = f.read(chunk_size)
            hasher.update(tail)

    # ファイルサイズも含める
    hasher.update(str(file_size).encode())

    return hasher.hexdigest()


def quick_hash(content: bytes) -> str:
    """バイト列のハッシュを計算。

    Args:
        content: バイト列

    Returns:
        SHA-256ハッシュ文字列
    """
    return hashlib.sha256(content).hexdigest()


def text_hash(text: str) -> str:
    """テキストのハッシュを計算。

    Args:
        text: テキスト

    Returns:
        SHA-256ハッシュ文字列
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
