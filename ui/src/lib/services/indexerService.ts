/**
 * インデックス関連のAPIサービス
 */

import { getApiBaseUrl } from '$lib/config';

const STORAGE_KEY = 'localdocsearch_watch_paths';

/** インデックス済みディレクトリ情報 */
export interface IndexedDirectory {
  path: string;
  file_count: number;
}

/** インデックス処理の統計情報 */
export interface IndexStats {
  pdf_count: number;
  vlm_pages_processed: number;
  image_count: number;
  audio_count: number;
  video_count: number;
  text_count: number;
  skipped_count: number;
}

/** インデックス処理の結果 */
export interface IndexResult {
  indexed_count: number;
  paths: string[];
  stats: IndexStats | null;
  processing_time_seconds: number | null;
}

/**
 * 指定パスのインデックス処理を実行
 * @param path インデックス対象のパス
 * @returns インデックス結果
 */
export async function indexPath(path: string): Promise<IndexResult> {
  const response = await fetch(`${getApiBaseUrl()}/api/documents/index`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, recursive: true }),
  });

  if (!response.ok) {
    throw new Error('インデックス化に失敗しました');
  }

  return response.json();
}

/**
 * インデックス済みディレクトリ一覧を取得
 * @returns ディレクトリ一覧
 */
export async function fetchIndexedDirectories(): Promise<IndexedDirectory[]> {
  const response = await fetch(`${getApiBaseUrl()}/api/documents/directories`);

  if (!response.ok) {
    throw new Error('ディレクトリ一覧の取得に失敗しました');
  }

  return response.json();
}

/**
 * ローカルストレージから監視パス一覧を取得
 * @returns 監視パス配列
 */
export function loadWatchPaths(): string[] {
  if (typeof window === 'undefined') {
    return [];
  }

  const saved = localStorage.getItem(STORAGE_KEY);
  if (!saved) {
    return [];
  }

  try {
    return JSON.parse(saved);
  } catch {
    return [];
  }
}

/**
 * 監視パス一覧をローカルストレージに保存
 * @param paths 監視パス配列
 */
export function saveWatchPaths(paths: string[]): void {
  if (typeof window === 'undefined') {
    return;
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(paths));
}

/**
 * 監視パスを追加
 * @param paths 現在のパス配列
 * @param newPath 追加するパス
 * @returns 追加後のパス配列（重複時はnull）
 */
export function addWatchPath(paths: string[], newPath: string): string[] | null {
  const trimmedPath = newPath.trim();

  if (!trimmedPath) {
    return null;
  }

  if (paths.includes(trimmedPath)) {
    return null;
  }

  const updated = [...paths, trimmedPath];
  saveWatchPaths(updated);
  return updated;
}

/**
 * 監視パスを削除
 * @param paths 現在のパス配列
 * @param index 削除するインデックス
 * @returns 削除後のパス配列
 */
export function removeWatchPath(paths: string[], index: number): string[] {
  const updated = paths.filter((_, i) => i !== index);
  saveWatchPaths(updated);
  return updated;
}

/**
 * インデックス結果を表示用メッセージにフォーマット
 * @param data インデックス結果
 * @returns フォーマットされたメッセージ
 */
export function formatIndexStats(data: IndexResult): string {
  const parts: string[] = [];

  if (data.stats) {
    const s = data.stats;
    if (s.pdf_count > 0) {
      let pdfInfo = `PDF: ${s.pdf_count}`;
      if (s.vlm_pages_processed > 0) {
        pdfInfo += ` (VLM: ${s.vlm_pages_processed}ページ)`;
      }
      parts.push(pdfInfo);
    }
    if (s.image_count > 0) parts.push(`画像: ${s.image_count}`);
    if (s.audio_count > 0) parts.push(`音声: ${s.audio_count}`);
    if (s.video_count > 0) parts.push(`動画: ${s.video_count}`);
    if (s.text_count > 0) parts.push(`テキスト: ${s.text_count}`);
  }

  let msg = `${data.indexed_count}件のファイルをインデックス化しました`;
  if (parts.length > 0) {
    msg += ` [${parts.join(', ')}]`;
  }
  if (data.processing_time_seconds) {
    msg += ` (${data.processing_time_seconds}秒)`;
  }

  return msg;
}
