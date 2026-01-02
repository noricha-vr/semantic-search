"""チャンキングユーティリティ。

長いテキストを適切なサイズに分割する。
"""

import re
from dataclasses import dataclass

from src.config.settings import get_settings


@dataclass
class ChunkResult:
    """チャンク結果。"""

    text: str
    chunk_index: int
    start_char: int
    end_char: int


class Chunker:
    """テキストチャンカー。"""

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        """初期化。

        Args:
            chunk_size: チャンクサイズ（文字数）
            chunk_overlap: オーバーラップ（文字数）
        """
        settings = get_settings()
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

    def _find_split_point(self, text: str, start: int, end: int) -> int:
        """テキストの適切な分割点を見つける。

        文境界（。！？.!?）、段落境界（改行）、単語境界（スペース）の順で探す。

        Args:
            text: テキスト
            start: 検索開始位置
            end: 検索終了位置

        Returns:
            分割位置
        """
        search_range = text[start:end]

        # 文境界を探す（後ろから）
        sentence_ends = list(re.finditer(r"[。！？.!?]+\s*", search_range))
        if sentence_ends:
            return start + sentence_ends[-1].end()

        # 段落境界を探す
        newline_match = search_range.rfind("\n")
        if newline_match != -1:
            return start + newline_match + 1

        # 単語境界を探す
        space_match = search_range.rfind(" ")
        if space_match != -1:
            return start + space_match + 1

        # 見つからなければ終了位置
        return end

    def chunk_text(self, text: str) -> list[ChunkResult]:
        """テキストをチャンクに分割。

        Args:
            text: テキスト

        Returns:
            チャンクのリスト
        """
        if not text or not text.strip():
            return []

        # 余分な空白を正規化
        text = re.sub(r"\s+", " ", text).strip()

        if len(text) <= self.chunk_size:
            return [
                ChunkResult(
                    text=text,
                    chunk_index=0,
                    start_char=0,
                    end_char=len(text),
                )
            ]

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            # 終了位置を計算
            end = min(start + self.chunk_size, len(text))

            # テキストの終端に達していない場合は適切な分割点を探す
            if end < len(text):
                # 分割点の検索範囲（チャンクサイズの80%〜100%）
                search_start = start + int(self.chunk_size * 0.8)
                split_point = self._find_split_point(text, search_start, end)
                end = split_point

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(
                    ChunkResult(
                        text=chunk_text,
                        chunk_index=chunk_index,
                        start_char=start,
                        end_char=end,
                    )
                )
                chunk_index += 1

            # 次のチャンクの開始位置（オーバーラップを考慮）
            start = end - self.chunk_overlap
            if start < 0:
                start = end

            # 無限ループ防止
            if start >= len(text) or (start == end and end == len(text)):
                break

        return chunks

    def chunk_with_timestamps(
        self,
        segments: list[dict],
        text_key: str = "text",
        start_key: str = "start",
        end_key: str = "end",
    ) -> list[dict]:
        """タイムスタンプ付きセグメントをチャンク化。

        Args:
            segments: セグメントのリスト
            text_key: テキストのキー名
            start_key: 開始時間のキー名
            end_key: 終了時間のキー名

        Returns:
            チャンク化されたセグメントのリスト
        """
        if not segments:
            return []

        chunks = []
        current_chunk = {
            "text": "",
            "start_time": None,
            "end_time": None,
            "chunk_index": 0,
        }

        for segment in segments:
            text = segment.get(text_key, "")
            start = segment.get(start_key)
            end = segment.get(end_key)

            if not text.strip():
                continue

            if current_chunk["start_time"] is None:
                current_chunk["start_time"] = start

            potential_text = current_chunk["text"] + " " + text if current_chunk["text"] else text

            if len(potential_text) > self.chunk_size:
                # 現在のチャンクを確定
                if current_chunk["text"]:
                    chunks.append(current_chunk.copy())

                # 新しいチャンクを開始
                current_chunk = {
                    "text": text,
                    "start_time": start,
                    "end_time": end,
                    "chunk_index": len(chunks),
                }
            else:
                current_chunk["text"] = potential_text.strip()
                current_chunk["end_time"] = end

        # 最後のチャンクを追加
        if current_chunk["text"]:
            chunks.append(current_chunk)

        return chunks
