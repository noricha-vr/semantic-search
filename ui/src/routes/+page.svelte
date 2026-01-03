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

	$effect(() => {
		if (sortBy === 'score') {
			results = [...results].sort((a, b) => b.score - a.score);
		} else {
			results = [...results].sort((a, b) => a.filename.localeCompare(b.filename));
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

<div class="min-h-screen bg-gray-50">
	<header class="bg-white shadow-sm border-b border-gray-200">
		<div class="max-w-4xl mx-auto px-4 py-6">
			<div class="flex items-center justify-between mb-4">
				<h1 class="text-2xl font-bold text-gray-900">LocalDocSearch</h1>
				<nav class="flex gap-4">
					<a href="/status" class="text-gray-600 hover:text-gray-900">ダッシュボード</a>
					<a href="/settings" class="text-gray-600 hover:text-gray-900">設定</a>
				</nav>
			</div>
			<SearchBar onSearch={handleSearch} {isLoading} />
		</div>
	</header>

	<main class="max-w-4xl mx-auto px-4 py-6">
		{#if errorMessage}
			<div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
				{errorMessage}
			</div>
		{/if}

		{#if isLoading}
			<div class="flex justify-center py-12">
				<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
			</div>
		{:else if results.length > 0}
			<div class="flex items-center justify-between mb-4">
				<p class="text-sm text-gray-500">
					「{query}」の検索結果: {results.length}件
					{#if currentMediaType}
						<span class="ml-1 px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">
							{getMediaTypeLabel(currentMediaType)}
						</span>
					{/if}
				</p>
				<div class="flex items-center gap-2 text-sm">
					<span class="text-gray-500">並び替え:</span>
					<select
						bind:value={sortBy}
						class="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
					>
						<option value="score">関連度順</option>
						<option value="filename">ファイル名順</option>
					</select>
				</div>
			</div>
			<SearchResults {results} {query} onOpen={handleOpenFile} onReveal={handleRevealFile} />
		{:else if query}
			<p class="text-center text-gray-500 py-12">
				「{query}」に一致する結果が見つかりませんでした
			</p>
		{:else}
			<div class="text-center text-gray-500 py-12">
				<p class="text-lg mb-2">ドキュメントを検索</p>
				<p class="text-sm">画像、PDF、動画、音声ファイルを自然言語で検索できます</p>
			</div>
		{/if}
	</main>
</div>
