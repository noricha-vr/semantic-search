"""ドキュメント処理プロセッサ。

PDF、Office、テキストファイルをインデックス化する。
"""

import os
import signal
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config.logging import get_logger
from src.config.settings import get_settings
from src.embeddings.ollama_embedding import OllamaEmbeddingClient
from src.indexer.processors.base import BaseMediaProcessor
from src.ocr.vlm_client import VLMClient
from src.processors.chunker import Chunker
from src.processors.office_processor import OfficeProcessor
from src.processors.pdf_processor import PDFProcessor, PDFResult
from src.processors.text_processor import TextProcessor
from src.storage.lancedb_client import LanceDBClient
from src.storage.models import DocumentRecord
from src.storage.schema import MediaType
from src.storage.sqlite_client import SQLiteClient

logger = get_logger()


class VLMTimeoutError(Exception):
    """VLM処理がタイムアウトした場合の例外。"""

    pass


class DocumentProcessor(BaseMediaProcessor):
    """ドキュメント処理プロセッサ。

    PDF、Office、テキストファイルを処理してインデックス化する。
    VLMフォールバックによるPDF画像処理も含む。
    """

    def __init__(
        self,
        pdf_processor: PDFProcessor | None = None,
        text_processor: TextProcessor | None = None,
        office_processor: OfficeProcessor | None = None,
        chunker: Chunker | None = None,
        embedding_client: OllamaEmbeddingClient | None = None,
        lancedb_client: LanceDBClient | None = None,
        sqlite_client: SQLiteClient | None = None,
    ):
        """初期化。

        Args:
            pdf_processor: PDFプロセッサ（テスト用に差し替え可能）
            text_processor: テキストプロセッサ（テスト用に差し替え可能）
            office_processor: Officeプロセッサ（テスト用に差し替え可能）
            chunker: チャンカー（テスト用に差し替え可能）
            embedding_client: 埋め込みクライアント（テスト用に差し替え可能）
            lancedb_client: LanceDBクライアント（テスト用に差し替え可能）
            sqlite_client: SQLiteクライアント（テスト用に差し替え可能）
        """
        self.settings = get_settings()
        self.pdf_processor = pdf_processor or PDFProcessor()
        self.text_processor = text_processor or TextProcessor()
        self.office_processor = office_processor or OfficeProcessor()
        self.chunker = chunker or Chunker()
        self.embedding_client = embedding_client or OllamaEmbeddingClient()
        self.lancedb_client = lancedb_client or LanceDBClient()
        self.sqlite_client = sqlite_client or SQLiteClient()
        # PDF VLMフォールバック用（設定されたモデルを使用）
        self._pdf_vlm_client: VLMClient | None = None
        # 処理統計の追跡
        self._vlm_pages_processed: int = 0

    def can_process(self, file_path: Path) -> bool:
        """このプロセッサで処理可能か判定。

        Args:
            file_path: ファイルパス

        Returns:
            処理可能ならTrue
        """
        return (
            self.pdf_processor.is_supported(file_path)
            or self.office_processor.is_supported(file_path)
            or self.text_processor.is_supported(file_path)
        )

    def _create_document_record(
        self,
        file_path: Path,
        content_hash: str,
    ) -> dict[str, Any]:
        """ドキュメントレコードを作成。

        Args:
            file_path: ファイルパス
            content_hash: コンテンツハッシュ

        Returns:
            ドキュメントレコード（後方互換性のためdict形式）
        """
        stat = file_path.stat()
        now = datetime.now(timezone.utc)

        record = DocumentRecord(
            id=str(uuid.uuid4()),
            content_hash=content_hash,
            path=str(file_path.absolute()),
            filename=file_path.name,
            extension=file_path.suffix.lower(),
            media_type=MediaType.DOCUMENT.value,
            size=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            indexed_at=now,
        )
        return record.model_dump()

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

        # VLM処理ページ数を追跡
        self._vlm_pages_processed += successful

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

    def process(self, file_path: Path, content_hash: str) -> dict[str, Any] | None:
        """ドキュメントをインデックス化。

        Args:
            file_path: ファイルパス
            content_hash: コンテンツハッシュ

        Returns:
            ドキュメントレコードまたはNone
        """
        # テキスト抽出
        text = self._extract_text(file_path)
        if not text:
            logger.warning(f"No text extracted from: {file_path}")
            return None

        # ドキュメントレコード作成
        doc_record = self._create_document_record(file_path, content_hash)
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
                "media_type": MediaType.DOCUMENT.value,
            }
            chunk_records.append(chunk_record)
            fts_records.append(
                {
                    "id": chunk_id,
                    "document_id": document_id,
                    "text": chunk.text,
                    "path": str(file_path.absolute()),
                    "filename": file_path.name,
                }
            )

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

    @property
    def vlm_pages_processed(self) -> int:
        """VLM処理されたページ数を返す。"""
        return self._vlm_pages_processed
