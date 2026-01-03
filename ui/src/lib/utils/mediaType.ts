/**
 * メディアタイプのラベルと表示ユーティリティ
 */

/** メディアタイプからラベルへのマッピング */
export const MEDIA_TYPE_LABELS: Record<string, string> = {
  image: '画像',
  video: '動画',
  audio: '音声',
  pdf: 'PDF',
  document: 'ドキュメント',
  text: 'テキスト',
};

/**
 * メディアタイプに対応する日本語ラベルを取得
 * @param type メディアタイプ
 * @returns 日本語ラベル（未定義の場合は元のtype文字列）
 */
export function getMediaTypeLabel(type: string): string {
  return MEDIA_TYPE_LABELS[type] || type;
}

/**
 * メディアタイプに対応するTailwind CSSカラークラスを取得
 * @param type メディアタイプ
 * @returns Tailwind CSSクラス文字列
 */
export function getMediaTypeColor(type: string): string {
  const colors: Record<string, string> = {
    image: 'bg-green-100 text-green-800',
    video: 'bg-purple-100 text-purple-800',
    audio: 'bg-yellow-100 text-yellow-800',
    pdf: 'bg-red-100 text-red-800',
    document: 'bg-blue-100 text-blue-800',
    text: 'bg-gray-100 text-gray-800',
  };
  return colors[type] || 'bg-gray-100 text-gray-800';
}

/**
 * メディアタイプに対応するFontAwesomeアイコンクラスを取得
 * @param type メディアタイプ
 * @returns FontAwesomeアイコンクラス
 */
export function getMediaTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    image: 'fa-image',
    video: 'fa-video',
    audio: 'fa-music',
    pdf: 'fa-file-pdf',
    document: 'fa-file-alt',
    text: 'fa-file-alt',
  };
  return icons[type] || 'fa-file-alt';
}
