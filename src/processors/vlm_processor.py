"""VLMプロセッサ。

画像やPDFページをVLMで分析する処理を提供する。
"""

import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import Any

from src.config.logging import get_logger
from src.config.settings import get_settings
from src.ocr.vlm_client import VLMClient
from src.processors.pdf_processor import PDFProcessor, PDFResult

logger = get_logger()


class VLMTimeoutError(Exception):
    """VLM処理がタイムアウトした場合の例外。"""

    pass


class VLMProcessor:
    """VLMプロセッサ。

    画像やPDFページをVLMで分析する。
    ThreadPoolExecutorのtimeoutを使用したタイムアウト制御を提供。
    """

    def __init__(
        self,
        vlm_client: VLMClient | None = None,
        pdf_processor: PDFProcessor | None = None,
        model: str | None = None,
    ):
        """初期化。

        Args:
            vlm_client: VLMクライアント（テスト用に差し替え可能）
            pdf_processor: PDFプロセッサ（テスト用に差し替え可能）
            model: 使用するVLMモデル名
        """
        self.settings = get_settings()
        self._model = model or self.settings.pdf_vlm_model
        self._vlm_client = vlm_client
        self._pdf_processor = pdf_processor
        self._vlm_pages_processed: int = 0

    def _get_vlm_client(self) -> VLMClient:
        """VLMクライアントを取得（遅延初期化）。"""
        if self._vlm_client is None:
            self._vlm_client = VLMClient(model=self._model)
        return self._vlm_client

    def _get_pdf_processor(self) -> PDFProcessor:
        """PDFプロセッサを取得（遅延初期化）。"""
        if self._pdf_processor is None:
            self._pdf_processor = PDFProcessor()
        return self._pdf_processor

    def extract_text_with_timeout(
        self,
        image_path: Path,
        timeout_seconds: int,
    ) -> str:
        """タイムアウト付きでVLMテキスト抽出。

        ThreadPoolExecutorを使用してタイムアウト制御を行う。

        Args:
            image_path: 画像ファイルパス
            timeout_seconds: タイムアウト秒数

        Returns:
            抽出されたテキスト

        Raises:
            VLMTimeoutError: タイムアウト時
        """
        vlm_client = self._get_vlm_client()

        def extract():
            return vlm_client.extract_text(image_path)

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(extract)
            try:
                return future.result(timeout=timeout_seconds)
            except FuturesTimeoutError:
                raise VLMTimeoutError(
                    f"VLM processing timed out after {timeout_seconds}s"
                )

    def process_image(self, image_path: Path, timeout_seconds: int | None = None) -> str | None:
        """画像をVLMで分析してテキストを抽出。

        Args:
            image_path: 画像ファイルパス
            timeout_seconds: タイムアウト秒数（Noneの場合は設定から取得）

        Returns:
            抽出されたテキスト、失敗時はNone
        """
        if timeout_seconds is None:
            timeout_seconds = self.settings.pdf_vlm_timeout

        try:
            return self.extract_text_with_timeout(image_path, timeout_seconds)
        except VLMTimeoutError:
            logger.warning(f"VLM processing timed out for {image_path}")
            return None
        except Exception as e:
            logger.error(f"VLM processing failed for {image_path}: {e}")
            return None

    def process_pdf_pages(
        self,
        file_path: Path | str,
        pdf_result: PDFResult,
    ) -> str:
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
        pdf_processor = self._get_pdf_processor()
        image_paths = pdf_processor.render_pages_to_images(file_path, pages_to_process)

        timeout_seconds = self.settings.pdf_vlm_timeout
        successful = 0
        failed = 0
        timed_out = 0

        try:
            if workers <= 1:
                # 順次処理
                for i, (page_num, image_path) in enumerate(
                    zip(pages_to_process, image_paths)
                ):
                    progress = f"[{i + 1}/{total_pages}]"
                    logger.info(f"{progress} Processing page {page_num + 1} with VLM...")

                    try:
                        text = self.extract_text_with_timeout(image_path, timeout_seconds)
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
                results = self._process_pages_parallel(
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

    def _process_pages_parallel(
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
            vlm_client = VLMClient(model=self._model)
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

    @property
    def vlm_pages_processed(self) -> int:
        """VLM処理されたページ数を返す。"""
        return self._vlm_pages_processed
