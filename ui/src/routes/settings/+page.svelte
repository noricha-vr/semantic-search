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

<div class="min-h-screen">
	<header class="header sticky top-0 z-10">
		<div class="max-w-4xl mx-auto px-6 py-5">
			<div class="flex items-center justify-between">
				<h1 class="text-[22px] font-semibold text-[#1d1d1f]">
					<i class="fa-solid fa-gear mr-2 text-[#007aff]"></i>
					設定
				</h1>
				<a href="/" class="nav-link">
					<i class="fa-solid fa-arrow-left mr-1.5"></i>
					検索に戻る
				</a>
			</div>
		</div>
	</header>

	<main class="max-w-4xl mx-auto px-6 py-6">
		<IndexingStatus {isIndexing} {indexingPath} />

		{#if message}
			<div class="alert mb-5 {messageType === 'success' ? 'alert-success' : messageType === 'error' ? 'alert-error' : 'alert-info'}">
				{#if messageType === 'success'}
					<i class="fa-solid fa-circle-check mr-2"></i>
				{:else if messageType === 'error'}
					<i class="fa-solid fa-circle-exclamation mr-2"></i>
				{:else}
					<i class="fa-solid fa-circle-info mr-2"></i>
				{/if}
				{message}
			</div>
		{/if}

		<div class="surface p-6 mb-5">
			<h2 class="text-[17px] font-semibold text-[#1d1d1f] mb-4">
				<i class="fa-solid fa-eye mr-2 text-[#007aff]"></i>
				監視パス
			</h2>

			<IndexPathForm disabled={isIndexing} onAddPath={handleAddPath} />

			<WatchPathList
				{watchPaths}
				{isIndexing}
				{indexingPath}
				onIndex={handleIndexPath}
				onRemove={handleRemovePath}
			/>
		</div>

		<div class="surface p-6 mb-5">
			<h2 class="text-[17px] font-semibold text-[#1d1d1f] mb-4">
				<i class="fa-solid fa-bolt mr-2 text-[#ff9500]"></i>
				クイックインデックス
			</h2>
			<p class="text-[14px] text-[#86868b] mb-4">
				よく使うパスをすばやくインデックス化できます
			</p>

			<div class="grid grid-cols-2 gap-3">
				<button
					onclick={() => handleIndexPath('~/Documents')}
					disabled={isIndexing}
					class="quick-action"
				>
					<span class="quick-action-title">
						<i class="fa-solid fa-folder-open mr-2 text-[#007aff]"></i>
						Documents
					</span>
					<span class="quick-action-path">~/Documents</span>
				</button>
				<button
					onclick={() => handleIndexPath('~/Desktop')}
					disabled={isIndexing}
					class="quick-action"
				>
					<span class="quick-action-title">
						<i class="fa-solid fa-desktop mr-2 text-[#34c759]"></i>
						Desktop
					</span>
					<span class="quick-action-path">~/Desktop</span>
				</button>
				<button
					onclick={() => handleIndexPath('~/Downloads')}
					disabled={isIndexing}
					class="quick-action"
				>
					<span class="quick-action-title">
						<i class="fa-solid fa-download mr-2 text-[#af52de]"></i>
						Downloads
					</span>
					<span class="quick-action-path">~/Downloads</span>
				</button>
				<button
					onclick={() => handleIndexPath('~/Pictures')}
					disabled={isIndexing}
					class="quick-action"
				>
					<span class="quick-action-title">
						<i class="fa-solid fa-image mr-2 text-[#ff9500]"></i>
						Pictures
					</span>
					<span class="quick-action-path">~/Pictures</span>
				</button>
			</div>
		</div>

		<div class="surface p-6">
			<div class="flex items-center justify-between mb-4">
				<h2 class="text-[17px] font-semibold text-[#1d1d1f]">
					<i class="fa-solid fa-database mr-2 text-[#007aff]"></i>
					インデックス済みディレクトリ
				</h2>
				<button
					onclick={loadIndexedDirectories}
					class="nav-link"
				>
					<i class="fa-solid fa-arrows-rotate mr-1"></i>
					更新
				</button>
			</div>

			{#if loadingDirectories}
				<div class="flex items-center justify-center py-8">
					<div class="spinner mr-3"></div>
					<span class="text-[14px] text-[#86868b]">読み込み中...</span>
				</div>
			{:else if indexedDirectories.length > 0}
				<div class="space-y-2">
					{#each indexedDirectories as dir}
						<div class="list-item">
							<div class="flex items-center gap-3">
								<i class="fa-solid fa-folder text-[#ff9500] text-lg"></i>
								<span class="text-[14px] text-[#1d1d1f] font-mono">{dir.path}</span>
							</div>
							<span class="badge badge-gray">
								{dir.file_count}ファイル
							</span>
						</div>
					{/each}
				</div>
				<p class="text-[13px] text-[#86868b] mt-4">
					<i class="fa-solid fa-chart-pie mr-1.5"></i>
					合計: {indexedDirectories.reduce((sum, d) => sum + d.file_count, 0)}ファイル
				</p>
			{:else}
				<div class="empty-state py-8">
					<i class="fa-regular fa-folder-open text-3xl mb-3 block"></i>
					<p class="text-[14px]">インデックス済みのディレクトリがありません</p>
				</div>
			{/if}
		</div>
	</main>
</div>
