<script lang="ts">
	import { onMount } from 'svelte';
	import { getApiBaseUrl } from '$lib/config';

	interface Stats {
		total_documents: number;
		by_media_type: Record<string, number>;
		total_chunks: number;
		last_indexed_at: string | null;
	}

	interface Document {
		id: string;
		path: string;
		filename: string;
		extension: string;
		media_type: string;
		size: number;
		indexed_at: string;
	}

	let stats = $state<Stats | null>(null);
	let recentDocs = $state<Document[]>([]);
	let isLoading = $state(true);
	let error = $state('');

	onMount(async () => {
		await loadData();
	});

	async function loadData() {
		isLoading = true;
		error = '';

		try {
			const [statsRes, docsRes] = await Promise.all([
				fetch(`${getApiBaseUrl()}/api/documents/stats`),
				fetch(`${getApiBaseUrl()}/api/documents?limit=5`)
			]);

			if (!statsRes.ok || !docsRes.ok) {
				throw new Error('データの取得に失敗しました');
			}

			stats = await statsRes.json();
			const docsData = await docsRes.json();
			recentDocs = docsData.documents;
		} catch (e) {
			error = e instanceof Error ? e.message : 'エラーが発生しました';
		} finally {
			isLoading = false;
		}
	}

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return 'N/A';
		const date = new Date(dateStr);
		return date.toLocaleString('ja-JP');
	}

	function getMediaTypeLabel(type: string): string {
		const labels: Record<string, string> = {
			document: 'ドキュメント',
			image: '画像',
			video: '動画',
			audio: '音声'
		};
		return labels[type] || type;
	}

	function formatSize(bytes: number): string {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}

	function getMediaTypeIcon(type: string): string {
		const icons: Record<string, string> = {
			document: 'D',
			image: 'I',
			video: 'V',
			audio: 'A'
		};
		return icons[type] || '?';
	}

	function getMediaTypeColor(type: string): string {
		const colors: Record<string, string> = {
			document: 'bg-blue-100 text-blue-700',
			image: 'bg-green-100 text-green-700',
			video: 'bg-purple-100 text-purple-700',
			audio: 'bg-orange-100 text-orange-700'
		};
		return colors[type] || 'bg-gray-100 text-gray-700';
	}

	async function openFile(path: string) {
		try {
			await fetch(`${getApiBaseUrl()}/api/actions/open`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ path })
			});
		} catch (e) {
			console.error('Failed to open file:', e);
		}
	}
</script>

<div class="min-h-screen bg-gray-50">
	<header class="bg-white shadow-sm border-b border-gray-200">
		<div class="max-w-4xl mx-auto px-4 py-6">
			<div class="flex items-center justify-between">
				<h1 class="text-2xl font-bold text-gray-900">ダッシュボード</h1>
				<a href="/" class="text-blue-500 hover:text-blue-600">検索に戻る</a>
			</div>
		</div>
	</header>

	<main class="max-w-4xl mx-auto px-4 py-6">
		{#if error}
			<div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
				{error}
				<button
					onclick={loadData}
					class="ml-2 underline hover:no-underline"
				>
					再試行
				</button>
			</div>
		{/if}

		{#if isLoading}
			<div class="flex justify-center py-12">
				<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
			</div>
		{:else if stats}
			<div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
				<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
					<h2 class="text-sm font-medium text-gray-500 mb-1">総ドキュメント数</h2>
					<p class="text-3xl font-bold text-gray-900">{stats.total_documents}</p>
				</div>

				<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
					<h2 class="text-sm font-medium text-gray-500 mb-1">総チャンク数</h2>
					<p class="text-3xl font-bold text-gray-900">{stats.total_chunks}</p>
				</div>

				<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
					<h2 class="text-sm font-medium text-gray-500 mb-1">最終インデックス</h2>
					<p class="text-lg font-medium text-gray-900">{formatDate(stats.last_indexed_at)}</p>
				</div>
			</div>

			<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
				<h2 class="text-lg font-semibold text-gray-900 mb-4">メディアタイプ別</h2>

				{#if Object.keys(stats.by_media_type).length > 0}
					<div class="space-y-3">
						{#each Object.entries(stats.by_media_type) as [type, count] (type)}
							<div class="flex items-center justify-between">
								<span class="text-gray-700">{getMediaTypeLabel(type)}</span>
								<div class="flex items-center gap-2">
									<div class="w-32 bg-gray-200 rounded-full h-2">
										<div
											class="bg-blue-500 h-2 rounded-full"
											style="width: {Math.min((count / stats.total_documents) * 100, 100)}%"
										></div>
									</div>
									<span class="text-gray-900 font-medium w-12 text-right">{count}</span>
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<p class="text-gray-500 text-center py-4">データがありません</p>
				{/if}
			</div>

			{#if recentDocs.length > 0}
				<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mt-6">
					<h2 class="text-lg font-semibold text-gray-900 mb-4">最近のドキュメント</h2>
					<ul class="space-y-2">
						{#each recentDocs as doc (doc.id)}
							<li class="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
								<div class="flex items-center gap-3 min-w-0">
									<span class="flex-shrink-0 w-8 h-8 rounded flex items-center justify-center text-sm font-medium {getMediaTypeColor(doc.media_type)}">
										{getMediaTypeIcon(doc.media_type)}
									</span>
									<div class="min-w-0">
										<p class="text-gray-900 truncate" title={doc.filename}>{doc.filename}</p>
										<p class="text-sm text-gray-500">{formatSize(doc.size)} - {formatDate(doc.indexed_at)}</p>
									</div>
								</div>
								<button
									onclick={() => openFile(doc.path)}
									class="flex-shrink-0 px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
								>
									開く
								</button>
							</li>
						{/each}
					</ul>
				</div>
			{/if}

			<div class="mt-6 flex justify-center">
				<button
					onclick={loadData}
					class="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
				>
					更新
				</button>
			</div>
		{/if}
	</main>
</div>
