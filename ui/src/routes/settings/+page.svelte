<script lang="ts">
	import { onMount } from 'svelte';
	import IndexPathForm from '$lib/components/settings/IndexPathForm.svelte';
	import WatchPathList from '$lib/components/settings/WatchPathList.svelte';
	import IndexingStatus from '$lib/components/settings/IndexingStatus.svelte';
	import {
		type IndexedDirectory,
		loadWatchPaths,
		addWatchPath,
		removeWatchPath,
		indexPath as indexPathApi,
		fetchIndexedDirectories,
		formatIndexStats
	} from '$lib/services/indexerService';

	let watchPaths = $state<string[]>([]);
	let message = $state('');
	let messageType = $state<'info' | 'success' | 'error'>('info');
	let indexedDirectories = $state<IndexedDirectory[]>([]);
	let loadingDirectories = $state(true);
	let isIndexing = $state(false);
	let indexingPath = $state('');

	async function loadIndexedDirectories() {
		loadingDirectories = true;
		try {
			indexedDirectories = await fetchIndexedDirectories();
		} catch (error) {
			console.error('Failed to fetch indexed directories:', error);
		} finally {
			loadingDirectories = false;
		}
	}

	onMount(() => {
		watchPaths = loadWatchPaths();
		loadIndexedDirectories();
	});

	function showMessage(msg: string, type: 'info' | 'success' | 'error' = 'info') {
		message = msg;
		messageType = type;
		setTimeout(() => (message = ''), 3000);
	}

	function handleAddPath(path: string) {
		const result = addWatchPath(watchPaths, path);
		if (result === null) {
			showMessage('このパスは既に追加されているか、無効です', 'error');
			return;
		}
		watchPaths = result;
		showMessage('パスを追加しました', 'success');
	}

	function handleRemovePath(index: number) {
		watchPaths = removeWatchPath(watchPaths, index);
		showMessage('パスを削除しました', 'info');
	}

	async function handleIndexPath(path: string) {
		if (isIndexing) return;

		isIndexing = true;
		indexingPath = path;
		message = '';

		try {
			const data = await indexPathApi(path);
			showMessage(formatIndexStats(data), 'success');
			await loadIndexedDirectories();
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
		<IndexingStatus {isIndexing} {indexingPath} />

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

			<IndexPathForm disabled={isIndexing} onAddPath={handleAddPath} />

			<WatchPathList
				{watchPaths}
				{isIndexing}
				{indexingPath}
				onIndex={handleIndexPath}
				onRemove={handleRemovePath}
			/>
		</div>

		<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
			<h2 class="text-lg font-semibold text-gray-900 mb-4">クイックインデックス</h2>
			<p class="text-gray-600 mb-4">
				よく使うパスをすばやくインデックス化できます
			</p>

			<div class="grid grid-cols-2 gap-2">
				<button
					onclick={() => handleIndexPath('~/Documents')}
					disabled={isIndexing}
					class="p-3 text-left bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
				>
					<span class="font-medium">Documents</span>
					<span class="block text-sm text-gray-500">~/Documents</span>
				</button>
				<button
					onclick={() => handleIndexPath('~/Desktop')}
					disabled={isIndexing}
					class="p-3 text-left bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
				>
					<span class="font-medium">Desktop</span>
					<span class="block text-sm text-gray-500">~/Desktop</span>
				</button>
				<button
					onclick={() => handleIndexPath('~/Downloads')}
					disabled={isIndexing}
					class="p-3 text-left bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
				>
					<span class="font-medium">Downloads</span>
					<span class="block text-sm text-gray-500">~/Downloads</span>
				</button>
				<button
					onclick={() => handleIndexPath('~/Pictures')}
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
					onclick={loadIndexedDirectories}
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
