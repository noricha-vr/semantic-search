<script lang="ts">
	import SearchBar from '$lib/components/SearchBar.svelte';
	import SearchResults from '$lib/components/SearchResults.svelte';
	import { getApiBaseUrl } from '$lib/config';
	import { getMediaTypeLabel } from '$lib/utils/mediaType';

	interface SearchResult {
		chunk_id: string;
		document_id: string;
		text: string;
		path: string;
		filename: string;
		media_type: string;
		score: number;
		start_time?: number;
		end_time?: number;
	}

	let results = $state<SearchResult[]>([]);
	let isLoading = $state(false);
	let query = $state('');
	let currentMediaType = $state<string | null>(null);
	let errorMessage = $state('');
	let sortBy = $state<'score' | 'filename'>('score');

	let prevSortBy = $state(sortBy);
	$effect(() => {
		if (sortBy !== prevSortBy) {
			prevSortBy = sortBy;
			if (sortBy === 'score') {
				results = [...results].sort((a, b) => b.score - a.score);
			} else {
				results = [...results].sort((a, b) => a.filename.localeCompare(b.filename));
			}
		}
	});

	async function handleSearch(searchQuery: string, mediaType: string | null = null) {
		if (!searchQuery.trim()) {
			results = [];
			return;
		}

		query = searchQuery;
		currentMediaType = mediaType;
		isLoading = true;
		errorMessage = '';

		try {
			let url = `${getApiBaseUrl()}/api/search?q=${encodeURIComponent(searchQuery)}&limit=20`;
			if (mediaType) {
				url += `&media_type=${encodeURIComponent(mediaType)}`;
			}

			const response = await fetch(url);

			if (!response.ok) {
				throw new Error('検索に失敗しました');
			}

			const data = await response.json();
			results = data.results;
		} catch (error) {
			console.error('Search error:', error);
			errorMessage = error instanceof Error ? error.message : '検索エラーが発生しました';
			results = [];
		} finally {
			isLoading = false;
		}
	}

	async function handleOpenFile(result: SearchResult) {
		try {
			await fetch(`${getApiBaseUrl()}/api/actions/open`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					path: result.path,
					start_time: result.start_time
				})
			});
		} catch (error) {
			console.error('Failed to open file:', error);
		}
	}

	async function handleRevealFile(result: SearchResult) {
		try {
			await fetch(`${getApiBaseUrl()}/api/actions/reveal`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ path: result.path })
			});
		} catch (error) {
			console.error('Failed to reveal file:', error);
		}
	}
</script>

<div class="min-h-screen">
	<header class="header sticky top-0 z-10">
		<div class="max-w-4xl mx-auto px-6 py-5">
			<div class="flex items-center justify-between mb-5">
				<h1 class="text-[22px] font-semibold text-[#1d1d1f]">
					<i class="fa-solid fa-magnifying-glass mr-2 text-[#007aff]"></i>
					LocalDocSearch
				</h1>
				<nav class="flex gap-5">
					<a href="/status" class="nav-link">
						<i class="fa-solid fa-chart-simple mr-1.5"></i>
						ダッシュボード
					</a>
					<a href="/settings" class="nav-link">
						<i class="fa-solid fa-gear mr-1.5"></i>
						設定
					</a>
				</nav>
			</div>
			<SearchBar onSearch={handleSearch} {isLoading} />
		</div>
	</header>

	<main class="max-w-4xl mx-auto px-6 py-6">
		{#if errorMessage}
			<div class="alert alert-error mb-5">
				<i class="fa-solid fa-circle-exclamation mr-2"></i>
				{errorMessage}
			</div>
		{/if}

		{#if isLoading}
			<div class="flex justify-center py-16">
				<div class="spinner"></div>
			</div>
		{:else if results.length > 0}
			<div class="flex items-center justify-between mb-5">
				<p class="text-[14px] text-[#86868b]">
					<i class="fa-solid fa-search mr-1.5"></i>
					「{query}」の検索結果: <span class="font-medium text-[#1d1d1f]">{results.length}件</span>
					{#if currentMediaType}
						<span class="badge badge-accent ml-2">
							{getMediaTypeLabel(currentMediaType)}
						</span>
					{/if}
				</p>
				<div class="flex items-center gap-2">
					<span class="text-[14px] text-[#86868b]">
						<i class="fa-solid fa-arrow-down-wide-short mr-1"></i>
						並び替え:
					</span>
					<select
						bind:value={sortBy}
						class="input-field py-1.5 px-3 text-[14px]"
					>
						<option value="score">関連度順</option>
						<option value="filename">ファイル名順</option>
					</select>
				</div>
			</div>
			<SearchResults {results} {query} onOpen={handleOpenFile} onReveal={handleRevealFile} />
		{:else if query}
			<div class="empty-state">
				<i class="fa-regular fa-folder-open text-4xl text-[#86868b] mb-4 block"></i>
				<p class="empty-state-title">結果が見つかりませんでした</p>
				<p class="empty-state-description">
					「{query}」に一致するドキュメントはありません。別のキーワードをお試しください。
				</p>
			</div>
		{:else}
			<div class="empty-state">
				<i class="fa-solid fa-magnifying-glass text-4xl text-[#86868b] mb-4 block"></i>
				<p class="empty-state-title">ドキュメントを検索</p>
				<p class="empty-state-description">
					画像、PDF、動画、音声ファイルを自然言語で検索できます
				</p>
			</div>
		{/if}
	</main>
</div>
