<script lang="ts">
	import { onMount } from 'svelte';
	import { getApiBaseUrl } from '$lib/config';

	const STORAGE_KEY = 'localdocsearch_watch_paths';

	interface IndexedDirectory {
		path: string;
		file_count: number;
	}

	interface IndexStats {
		pdf_count: number;
		vlm_pages_processed: number;
		image_count: number;
		audio_count: number;
		video_count: number;
		text_count: number;
		skipped_count: number;
	}

	interface IndexResult {
		indexed_count: number;
		paths: string[];
		stats: IndexStats | null;
		processing_time_seconds: number | null;
	}

	let watchPaths = $state<string[]>([]);
	let newPath = $state('');
	let message = $state('');
	let messageType = $state<'info' | 'success' | 'error'>('info');
	let indexedDirectories = $state<IndexedDirectory[]>([]);
	let loadingDirectories = $state(true);
	let isIndexing = $state(false);
	let indexingPath = $state('');

	async function fetchIndexedDirectories() {
		loadingDirectories = true;
		try {
			const response = await fetch(`${getApiBaseUrl()}/api/documents/directories`);
			if (response.ok) {
				indexedDirectories = await response.json();
			}
		} catch (error) {
			console.error('Failed to fetch indexed directories:', error);
		} finally {
			loadingDirectories = false;
		}
	}

	onMount(() => {
		const saved = localStorage.getItem(STORAGE_KEY);
		if (saved) {
			try {
				watchPaths = JSON.parse(saved);
			} catch {
				watchPaths = [];
			}
		}
		fetchIndexedDirectories();
	});

	function saveWatchPaths() {
		localStorage.setItem(STORAGE_KEY, JSON.stringify(watchPaths));
	}

	function showMessage(msg: string, type: 'info' | 'success' | 'error' = 'info') {
		message = msg;
		messageType = type;
		setTimeout(() => (message = ''), 3000);
	}

	async function addPath() {
		if (!newPath.trim()) return;

		const path = newPath.trim();
		if (watchPaths.includes(path)) {
			showMessage('このパスは既に追加されています', 'error');
			return;
		}

		watchPaths = [...watchPaths, path];
		saveWatchPaths();
		newPath = '';
		showMessage('パスを追加しました', 'success');
	}

	function removePath(index: number) {
		watchPaths = watchPaths.filter((_, i) => i !== index);
		saveWatchPaths();
		showMessage('パスを削除しました', 'info');
	}

	function formatStats(data: IndexResult): string {
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

	async function indexPath(path: string) {
		if (isIndexing) return;

		isIndexing = true;
		indexingPath = path;
		showMessage('', 'info'); // メッセージをクリア

		try {
			const response = await fetch(`${getApiBaseUrl()}/api/documents/index`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ path, recursive: true })
			});

			if (!response.ok) {
				throw new Error('インデックス化に失敗しました');
			}

			const data: IndexResult = await response.json();
			showMessage(formatStats(data), 'success');
			// インデックス済みディレクトリを更新
			await fetchIndexedDirectories();
		} catch (error) {
			showMessage(error instanceof Error ? error.message : 'エラーが発生しました', 'error');
		} finally {
			isIndexing = false;
			indexingPath = '';
		}
	}
</script>

<div class="min-h-screen bg-gray-50">
	<header class="bg-white shadow-sm border-b border-gray-200">
		<div class="max-w-4xl mx-auto px-4 py-6">
			<div class="flex items-center justify-between">
				<h1 class="text-2xl font-bold text-gray-900">設定</h1>
				<a href="/" class="text-blue-500 hover:text-blue-600">検索に戻る</a>
			</div>
		</div>
	</header>

	<main class="max-w-4xl mx-auto px-4 py-6">
		{#if isIndexing}
			<div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
				<div class="flex items-center gap-3">
					<div class="animate-spin rounded-full h-5 w-5 border-2 border-blue-500 border-t-transparent"></div>
					<div>
						<p class="font-medium text-blue-800">インデックス処理中...</p>
						<p class="text-sm text-blue-600">{indexingPath}</p>
						<p class="text-sm text-blue-500 mt-1">
							PDF VLM処理がある場合、数分かかることがあります
						</p>
					</div>
				</div>
			</div>
		{/if}

		{#if message}
			<div
				class="px-4 py-3 rounded mb-6 {messageType === 'success'
					? 'bg-green-50 border border-green-200 text-green-700'
					: messageType === 'error'
						? 'bg-red-50 border border-red-200 text-red-700'
						: 'bg-blue-50 border border-blue-200 text-blue-700'}"
			>
				{message}
			</div>
		{/if}

		<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
			<h2 class="text-lg font-semibold text-gray-900 mb-4">監視パス</h2>

			<div class="flex gap-2 mb-4">
				<input
					type="text"
					bind:value={newPath}
					placeholder="パスを入力 (例: ~/Documents)"
					class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
				/>
				<button
					onclick={addPath}
					class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
				>
					追加
				</button>
			</div>

			{#if watchPaths.length > 0}
				<ul class="space-y-2">
					{#each watchPaths as path, i (i)}
						<li class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
							<span class="text-gray-700">{path}</span>
							<div class="flex gap-2">
								<button
									onclick={() => indexPath(path)}
									disabled={isIndexing}
									class="px-3 py-1 text-sm bg-green-500 text-white rounded hover:bg-green-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
								>
									{isIndexing && indexingPath === path ? '処理中...' : 'インデックス'}
								</button>
								<button
									onclick={() => removePath(i)}
									disabled={isIndexing}
									class="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
								>
									削除
								</button>
							</div>
						</li>
					{/each}
				</ul>
			{:else}
				<p class="text-gray-500 text-center py-4">監視パスが設定されていません</p>
			{/if}
		</div>

		<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
			<h2 class="text-lg font-semibold text-gray-900 mb-4">クイックインデックス</h2>
			<p class="text-gray-600 mb-4">
				よく使うパスをすばやくインデックス化できます
			</p>

			<div class="grid grid-cols-2 gap-2">
				<button
					onclick={() => indexPath('~/Documents')}
					disabled={isIndexing}
					class="p-3 text-left bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
				>
					<span class="font-medium">Documents</span>
					<span class="block text-sm text-gray-500">~/Documents</span>
				</button>
				<button
					onclick={() => indexPath('~/Desktop')}
					disabled={isIndexing}
					class="p-3 text-left bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
				>
					<span class="font-medium">Desktop</span>
					<span class="block text-sm text-gray-500">~/Desktop</span>
				</button>
				<button
					onclick={() => indexPath('~/Downloads')}
					disabled={isIndexing}
					class="p-3 text-left bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
				>
					<span class="font-medium">Downloads</span>
					<span class="block text-sm text-gray-500">~/Downloads</span>
				</button>
				<button
					onclick={() => indexPath('~/Pictures')}
					disabled={isIndexing}
					class="p-3 text-left bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
				>
					<span class="font-medium">Pictures</span>
					<span class="block text-sm text-gray-500">~/Pictures</span>
				</button>
			</div>
		</div>

		<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
			<div class="flex items-center justify-between mb-4">
				<h2 class="text-lg font-semibold text-gray-900">インデックス済みディレクトリ</h2>
				<button
					onclick={fetchIndexedDirectories}
					class="text-sm text-blue-500 hover:text-blue-600"
				>
					更新
				</button>
			</div>

			{#if loadingDirectories}
				<div class="flex items-center justify-center py-8">
					<div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
					<span class="ml-2 text-gray-500">読み込み中...</span>
				</div>
			{:else if indexedDirectories.length > 0}
				<div class="space-y-2">
					{#each indexedDirectories as dir}
						<div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
							<div class="flex items-center gap-2">
								<i class="fa-solid fa-folder text-yellow-500"></i>
								<span class="text-gray-700 font-mono text-sm">{dir.path}</span>
							</div>
							<span class="text-sm text-gray-500 bg-gray-200 px-2 py-0.5 rounded">
								{dir.file_count}ファイル
							</span>
						</div>
					{/each}
				</div>
				<p class="text-sm text-gray-500 mt-4">
					合計: {indexedDirectories.reduce((sum, d) => sum + d.file_count, 0)}ファイル
				</p>
			{:else}
				<p class="text-gray-500 text-center py-8">
					インデックス済みのディレクトリがありません
				</p>
			{/if}
		</div>
	</main>
</div>
