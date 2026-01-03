"""ドキュメントインデクサー。

ファイルを処理してインデックス化する。
"""

import os
import signal
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class VLMTimeoutError(Exception):
    """VLM処理がタイムアウトした場合の例外。"""
    pass

from src.config.logging import get_logger
from src.config.settings import get_settings
from src.embeddings.ollama_embedding import OllamaEmbeddingClient
from src.indexer.hash_utils import calculate_file_hash
from src.ocr.vlm_client import VLMClient
from src.processors.audio_processor import AudioProcessor
from src.processors.chunker import Chunker
from src.processors.image_processor import ImageProcessor
from src.processors.office_processor import OfficeProcessor
from src.processors.pdf_processor import PDFProcessor, PDFResult
from src.processors.text_processor import TextProcessor
from src.processors.video_processor import VideoProcessor
from src.storage.lancedb_client import LanceDBClient
from src.storage.schema import MediaType
from src.storage.sqlite_client import SQLiteClient

logger = get_logger()


class DocumentIndexer:
    """ドキュメントインデクサー。"""

    # 画像拡張子
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".svg"}
    # 動画拡張子
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"}
    # 音声拡張子
    AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".wma"}

    def __init__(self):
        """初期化。"""
        self.settings = get_settings()
        self.pdf_processor = PDFProcessor()
        self.text_processor = TextProcessor()
        self.office_processor = OfficeProcessor()
        self.image_processor = ImageProcessor()
        self.audio_processor = AudioProcessor()
        self.video_processor = VideoProcessor()
        self.chunker = Chunker()
        self.embedding_client = OllamaEmbeddingClient()
        self.lancedb_client = LanceDBClient()
        self.sqlite_client = SQLiteClient()
        # PDF VLMフォールバック用（設定されたモデルを使用）
        self._pdf_vlm_client: VLMClient | None = None

    def _get_media_type(self, file_path: Path) -> MediaType:
        """ファイルのメディアタイプを判定。

        Args:
            file_path: ファイルパス

        Returns:
            メディアタイプ
        """
        suffix = file_path.suffix.lower()

        if suffix in self.IMAGE_EXTENSIONS:
            return MediaType.IMAGE
        elif suffix in self.VIDEO_EXTENSIONS:
            return MediaType.VIDEO
        elif suffix in self.AUDIO_EXTENSIONS:
            return MediaType.AUDIO
        else:
            return MediaType.DOCUMENT

    def _extract_text(self, file_path: Path) -> str | None:
        """ファイルからテキストを抽出。

        Args:
            file_path: ファイルパス

        Returns:
            抽出されたテキストまたはNone
        """
        try:
            if self.pdf_processor.is_supported(file_path):
                result = self.pdf_processor.extract_text(file_path)
                # VLMフォールバック処理
                if result.pages_needing_vlm and self.settings.pdf_vlm_fallback:
                    return self._process_pdf_with_vlm(file_path, result)
                return result.text
            elif self.office_processor.is_supported(file_path):
                result = self.office_processor.extract_text(file_path)
                return result.text
            elif self.text_processor.is_supported(file_path):
                result = self.text_processor.extract_text(file_path)
                return result.text
            else:
                logger.warning(f"Unsupported file type: {file_path}")
                return None
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {e}")
            return None

    def _get_pdf_vlm_client(self) -> VLMClient:
        """PDF VLM処理用のクライアントを取得（遅延初期化）。"""
        if self._pdf_vlm_client is None:
            self._pdf_vlm_client = VLMClient(model=self.settings.pdf_vlm_model)
        return self._pdf_vlm_client

    def _process_pdf_with_vlm(self, file_path: Path | str, pdf_result: PDFResult) -> str:
        """テキスト量が少ないPDFページをVLMで処理。

        Args:
            file_path: PDFファイルパス
            pdf_result: PDF処理結果

        Returns:
            テキスト抽出（VLM処理も含む）とマージされたテキスト
        """
        file_path = Path(file_path)
        vlm_texts: dict[int, str] = {}

        # 処理するページを制限
        pages_to_process = pdf_result.pages_needing_vlm
        max_pages = self.settings.pdf_vlm_max_pages
        if max_pages > 0 and len(pages_to_process) > max_pages:
            logger.warning(
                f"VLM page limit reached: {len(pages_to_process)} pages need VLM, "
                f"but max is {max_pages}. Processing first {max_pages} pages only."
            )
            pages_to_process = pages_to_process[:max_pages]

        total_pages = len(pages_to_process)
        workers = self.settings.pdf_vlm_workers

        logger.info(
            f"Starting VLM processing: {total_pages} pages from {file_path.name} "
            f"(workers: {workers})"
        )

        # VLMが必要なページを画像に変換して処理
        image_paths = self.pdf_processor.render_pages_to_images(
            file_path, pages_to_process
        )

        timeout_seconds = self.settings.pdf_vlm_timeout
        successful = 0
        failed = 0
        timed_out = 0

        try:
            if workers <= 1:
                # 順次処理（従来の方法）
                vlm_client = self._get_pdf_vlm_client()
                for i, (page_num, image_path) in enumerate(zip(pages_to_process, image_paths)):
                    progress = f"[{i + 1}/{total_pages}]"
                    logger.info(f"{progress} Processing page {page_num + 1} with VLM...")

                    try:
                        text = self._vlm_extract_with_timeout(
                            vlm_client, image_path, timeout_seconds
                        )
                        if text:
                            vlm_texts[page_num] = text
                            successful += 1
                            logger.info(
                                f"{progress} Page {page_num + 1}: extracted {len(text)} chars"
                            )
                        else:
                            failed += 1
                            logger.warning(f"{progress} Page {page_num + 1}: no text extracted")
                    except VLMTimeoutError:
                        timed_out += 1
                        logger.warning(
                            f"{progress} Page {page_num + 1}: timeout after {timeout_seconds}s"
                        )
                    except Exception as e:
                        failed += 1
                        logger.warning(f"{progress} Page {page_num + 1}: VLM error - {e}")
            else:
                # 並列処理
                results = self._process_vlm_parallel(
                    pages_to_process, image_paths, workers, timeout_seconds, total_pages
                )
                for page_num, result in results.items():
                    if result["status"] == "success":
                        vlm_texts[page_num] = result["text"]
                        successful += 1
                    elif result["status"] == "timeout":
                        timed_out += 1
                    else:
                        failed += 1
        finally:
            # 一時画像ファイルを削除
            for image_path in image_paths:
                try:
                    os.unlink(image_path)
                except Exception:
                    pass

        # 処理結果のサマリ
        logger.info(
            f"VLM processing complete: {successful} successful, "
            f"{failed} failed, {timed_out} timed out"
        )

        # テキストとVLM結果をマージ
        if not vlm_texts:
            return pdf_result.text

        return self._merge_pdf_texts(pdf_result, vlm_texts)

    def _process_vlm_parallel(
        self,
        pages: list[int],
        image_paths: list[Path],
        workers: int,
        timeout_seconds: int,
        total_pages: int,
    ) -> dict[int, dict[str, Any]]:
        """VLM処理を並列実行。

        Args:
            pages: ページ番号リスト
            image_paths: 画像パスリスト
            workers: ワーカー数
            timeout_seconds: タイムアウト秒数
            total_pages: 総ページ数（ログ用）

        Returns:
            ページ番号 -> 結果辞書のマッピング
        """
        results: dict[int, dict[str, Any]] = {}
        completed = 0

        def process_page(args: tuple[int, int, Path]) -> tuple[int, dict[str, Any]]:
            """1ページを処理する関数。"""
            idx, page_num, image_path = args
            # 各スレッドで新しいVLMクライアントを作成
            vlm_client = VLMClient(model=self.settings.pdf_vlm_model)
            try:
                text = vlm_client.extract_text(image_path)
                if text:
                    return page_num, {"status": "success", "text": text}
                return page_num, {"status": "failed", "error": "no text extracted"}
            except Exception as e:
                return page_num, {"status": "failed", "error": str(e)}

        with ThreadPoolExecutor(max_workers=workers) as executor:
            # 全タスクをサブミット
            futures = {
                executor.submit(process_page, (i, page_num, image_path)): (i, page_num)
                for i, (page_num, image_path) in enumerate(zip(pages, image_paths))
            }

            for future in futures:
                idx, page_num = futures[future]
                try:
                    result_page_num, result = future.result(timeout=timeout_seconds)
                    results[result_page_num] = result
                    completed += 1
                    progress = f"[{completed}/{total_pages}]"
                    if result["status"] == "success":
                        logger.info(
                            f"{progress} Page {page_num + 1}: extracted {len(result['text'])} chars"
                        )
                    else:
                        logger.warning(
                            f"{progress} Page {page_num + 1}: {result.get('error', 'failed')}"
                        )
                except FuturesTimeoutError:
                    results[page_num] = {"status": "timeout"}
                    completed += 1
                    logger.warning(
                        f"[{completed}/{total_pages}] Page {page_num + 1}: "
                        f"timeout after {timeout_seconds}s"
                    )
                except Exception as e:
                    results[page_num] = {"status": "failed", "error": str(e)}
                    completed += 1
                    logger.warning(
                        f"[{completed}/{total_pages}] Page {page_num + 1}: error - {e}"
                    )

        return results

    def _vlm_extract_with_timeout(
        self,
        vlm_client: VLMClient,
        image_path: Path,
        timeout_seconds: int,
    ) -> str:
        """タイムアウト付きでVLMテキスト抽出。

        Args:
            vlm_client: VLMクライアント
            image_path: 画像ファイルパス
            timeout_seconds: タイムアウト秒数

        Returns:
            抽出されたテキスト

        Raises:
            VLMTimeoutError: タイムアウト時
        """
        def timeout_handler(signum, frame):
            raise VLMTimeoutError(f"VLM processing timed out after {timeout_seconds}s")

        # シグナルハンドラを設定（Unixのみ）
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)

        try:
            return vlm_client.extract_text(image_path)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    def _merge_pdf_texts(
        self,
        pdf_result: PDFResult,
        vlm_texts: dict[int, str],
    ) -> str:
        """PDFテキストとVLM抽出テキストをマージ。

        Args:
            pdf_result: PDF処理結果
            vlm_texts: VLMで抽出したテキスト（ページ番号 -> テキスト）

        Returns:
            マージされたテキスト
        """
        if not vlm_texts:
            return pdf_result.text

        # VLM結果をマーカー付きで追加
        vlm_section = "\n\n--- VLM Extracted Text ---\n"
        for page_num in sorted(vlm_texts.keys()):
            vlm_section += f"\n[Page {page_num + 1}]\n{vlm_texts[page_num]}\n"

        combined = pdf_result.text + vlm_section

        logger.info(
            f"Merged PDF text: original {len(pdf_result.text)} chars, "
            f"VLM {sum(len(t) for t in vlm_texts.values())} chars from "
            f"{len(vlm_texts)} pages"
        )

        return combined

    def _create_document_record(
        self,
        file_path: Path,
        content_hash: str,
        media_type: MediaType,
    ) -> dict[str, Any]:
        """ドキュメントレコードを作成。

        Args:
            file_path: ファイルパス
            content_hash: コンテンツハッシュ
            media_type: メディアタイプ

        Returns:
            ドキュメントレコード
        """
        stat = file_path.stat()
        now = datetime.now(timezone.utc)

        return {
            "id": str(uuid.uuid4()),
            "content_hash": content_hash,
            "path": str(file_path.absolute()),
            "filename": file_path.name,
            "extension": file_path.suffix.lower(),
            "media_type": media_type.value,
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            "indexed_at": now,
            "is_deleted": False,
            "deleted_at": None,
            "duration_seconds": None,
            "width": None,
            "height": None,
        }

    def index_file(self, file_path: Path | str) -> dict[str, Any] | None:
        """ファイルをインデックス化。

        Args:
            file_path: ファイルパス

        Returns:
            インデックス化されたドキュメント情報またはNone
        """
        file_path = Path(file_path)
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return None

        # ハッシュ計算と重複チェック
        content_hash = calculate_file_hash(file_path)
        existing = self.sqlite_client.get_document_by_hash(content_hash)
        if existing:
            logger.info(f"File already indexed (same hash): {file_path}")
            return existing

        # メディアタイプ判定
        media_type = self._get_media_type(file_path)

        # 画像処理
        if media_type == MediaType.IMAGE:
            return self._index_image(file_path, content_hash)

        # 音声処理
        if media_type == MediaType.AUDIO:
            return self._index_audio(file_path, content_hash)

        # 動画処理
        if media_type == MediaType.VIDEO:
            return self._index_video(file_path, content_hash)

        # テキスト抽出
        text = self._extract_text(file_path)
        if not text:
            logger.warning(f"No text extracted from: {file_path}")
            return None

        # ドキュメントレコード作成
        doc_record = self._create_document_record(file_path, content_hash, media_type)
        document_id = doc_record["id"]

        # チャンキング
        chunks = self.chunker.chunk_text(text)
        if not chunks:
            logger.warning(f"No chunks created from: {file_path}")
            return None

        # Embedding生成
        chunk_texts = [c.text for c in chunks]
        embeddings = self.embedding_client.embed_batch(chunk_texts)

        # チャンクレコード作成
        chunk_records = []
        fts_records = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = str(uuid.uuid4())
            chunk_record = {
                "id": chunk_id,
                "document_id": document_id,
                "chunk_index": i,
                "text": chunk.text,
                "vector": embedding,
                "start_time": None,
                "end_time": None,
                "path": str(file_path.absolute()),
                "filename": file_path.name,
                "media_type": media_type.value,
            }
            chunk_records.append(chunk_record)
            fts_records.append({
                "id": chunk_id,
                "document_id": document_id,
                "text": chunk.text,
                "path": str(file_path.absolute()),
                "filename": file_path.name,
            })

        # データベースに保存
        self.sqlite_client.add_document(doc_record)
        self.lancedb_client.add_chunks(chunk_records)
        self.sqlite_client.add_chunks_fts(fts_records)

        logger.info(
            f"Indexed: {file_path}, "
            f"chunks: {len(chunk_records)}, "
            f"document_id: {document_id}"
        )

        return doc_record

    def index_directory(
        self,
        directory: Path | str,
        recursive: bool = True,
    ) -> list[dict[str, Any]]:
        """ディレクトリ内のファイルをインデックス化。

        Args:
            directory: ディレクトリパス
            recursive: サブディレクトリも処理するか

        Returns:
            インデックス化されたドキュメントのリスト
        """
        directory = Path(directory)
        if not directory.is_dir():
            logger.error(f"Not a directory: {directory}")
            return []

        indexed = []
        pattern = "**/*" if recursive else "*"

        for file_path in directory.glob(pattern):
            if file_path.is_file() and not file_path.name.startswith("."):
                result = self.index_file(file_path)
                if result:
                    indexed.append(result)

        logger.info(f"Indexed {len(indexed)} files from: {directory}")
        return indexed

    def _index_image(
        self,
        file_path: Path,
        content_hash: str,
    ) -> dict[str, Any] | None:
        """画像をインデックス化。

        Args:
            file_path: ファイルパス
            content_hash: コンテンツハッシュ

        Returns:
            ドキュメントレコードまたはNone
        """
        # ドキュメントレコード作成
        doc_record = self._create_document_record(file_path, content_hash, MediaType.IMAGE)
        document_id = doc_record["id"]

        # 画像メタデータを取得して更新
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                doc_record["width"] = img.width
                doc_record["height"] = img.height
        except Exception as e:
            logger.warning(f"Failed to get image metadata: {e}")

        # SQLiteにドキュメントを保存
        self.sqlite_client.add_document(doc_record)

        # 画像処理とインデックス化
        try:
            self.image_processor.index_image(file_path, document_id)
            logger.info(f"Indexed image: {file_path}, document_id: {document_id}")
            return doc_record
        except Exception as e:
            logger.error(f"Failed to index image {file_path}: {e}")
            # ドキュメントを削除
            self.sqlite_client.delete_document(document_id, hard_delete=True)
            return None

    def _index_audio(
        self,
        file_path: Path,
        content_hash: str,
    ) -> dict[str, Any] | None:
        """音声をインデックス化。

        Args:
            file_path: ファイルパス
            content_hash: コンテンツハッシュ

        Returns:
            ドキュメントレコードまたはNone
        """
        # ドキュメントレコード作成
        doc_record = self._create_document_record(file_path, content_hash, MediaType.AUDIO)
        document_id = doc_record["id"]

        # SQLiteにドキュメントを保存
        self.sqlite_client.add_document(doc_record)

        # 音声処理とインデックス化
        try:
            transcript = self.audio_processor.index_audio(file_path, document_id)
            if transcript:
                # duration を更新
                doc_record["duration_seconds"] = transcript.get("duration_seconds")
                self.sqlite_client.add_transcript(transcript)
                logger.info(f"Indexed audio: {file_path}, document_id: {document_id}")
                return doc_record
            else:
                # ドキュメントを削除
                self.sqlite_client.delete_document(document_id, hard_delete=True)
                return None
        except Exception as e:
            logger.error(f"Failed to index audio {file_path}: {e}")
            self.sqlite_client.delete_document(document_id, hard_delete=True)
            return None

    def _index_video(
        self,
        file_path: Path,
        content_hash: str,
    ) -> dict[str, Any] | None:
        """動画をインデックス化。

        Args:
            file_path: ファイルパス
            content_hash: コンテンツハッシュ

        Returns:
            ドキュメントレコードまたはNone
        """
        # ドキュメントレコード作成
        doc_record = self._create_document_record(file_path, content_hash, MediaType.VIDEO)
        document_id = doc_record["id"]

        # SQLiteにドキュメントを保存
        self.sqlite_client.add_document(doc_record)

        # 動画処理とインデックス化
        try:
            result = self.video_processor.index_video(file_path, document_id)
            if result:
                transcript = result.get("transcript")
                if transcript:
                    # duration と dimensions を更新
                    doc_record["duration_seconds"] = transcript.get("duration_seconds")
                    doc_record["width"] = result.get("width")
                    doc_record["height"] = result.get("height")
                    self.sqlite_client.add_transcript(transcript)
                logger.info(f"Indexed video: {file_path}, document_id: {document_id}")
                return doc_record
            else:
                # ドキュメントを削除
                self.sqlite_client.delete_document(document_id, hard_delete=True)
                return None
        except Exception as e:
            logger.error(f"Failed to index video {file_path}: {e}")
            self.sqlite_client.delete_document(document_id, hard_delete=True)
            return None

    def delete_document(self, document_id: str) -> None:
        """ドキュメントを削除。

        Args:
            document_id: ドキュメントID
        """
        self.lancedb_client.delete_by_document_id(document_id)
        self.sqlite_client.delete_document(document_id)
        logger.info(f"Deleted document: {document_id}")
