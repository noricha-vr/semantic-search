<script lang="ts">
	import SearchBar from '$lib/components/SearchBar.svelte';
	import SearchResults from '$lib/components/SearchResults.svelte';

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
	let errorMessage = $state('');

	async function handleSearch(searchQuery: string) {
		if (!searchQuery.trim()) {
			results = [];
			return;
		}

		query = searchQuery;
		isLoading = true;
		errorMessage = '';

		try {
			const response = await fetch(
				`http://localhost:8765/api/search?q=${encodeURIComponent(searchQuery)}&limit=20`
			);

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
			await fetch('http://localhost:8765/api/actions/open', {
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
			await fetch('http://localhost:8765/api/actions/reveal', {
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
			<h1 class="text-2xl font-bold text-gray-900 mb-4">LocalDocSearch</h1>
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
				<div
					class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"
				></div>
			</div>
		{:else if results.length > 0}
			<p class="text-sm text-gray-500 mb-4">
				「{query}」の検索結果: {results.length}件
			</p>
			<SearchResults
				{results}
				onOpen={handleOpenFile}
				onReveal={handleRevealFile}
			/>
		{:else if query}
			<p class="text-center text-gray-500 py-12">
				「{query}」に一致する結果が見つかりませんでした
			</p>
		{:else}
			<div class="text-center text-gray-500 py-12">
				<p class="text-lg mb-2">ドキュメントを検索</p>
				<p class="text-sm">
					画像、PDF、動画、音声ファイルを自然言語で検索できます
				</p>
			</div>
		{/if}
	</main>
</div>
