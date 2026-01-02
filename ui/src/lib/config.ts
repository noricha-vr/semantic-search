/**
 * API設定
 *
 * ブラウザのホスト名を使用してAPIエンドポイントを動的に決定
 */

const API_PORT = 2602;

/**
 * APIのベースURLを取得
 * 開発時はlocalhost、本番時は現在のホスト名を使用
 */
export function getApiBaseUrl(): string {
	if (typeof window === 'undefined') {
		// SSR時
		return `http://localhost:${API_PORT}`;
	}

	const hostname = window.location.hostname;
	return `http://${hostname}:${API_PORT}`;
}

export const API_BASE_URL = typeof window !== 'undefined'
	? getApiBaseUrl()
	: `http://localhost:${API_PORT}`;
