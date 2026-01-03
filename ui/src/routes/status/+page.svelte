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
			document: 'fa-file-alt',
			image: 'fa-image',
			video: 'fa-video',
			audio: 'fa-music'
		};
		return icons[type] || 'fa-file';
	}

	function getFileIconClass(type: string): string {
		const classes: Record<string, string> = {
			document: 'file-icon-document',
			image: 'file-icon-image',
			video: 'file-icon-video',
			audio: 'file-icon-audio'
		};
		return classes[type] || 'file-icon-document';
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

<div class="min-h-screen">
	<header class="header sticky top-0 z-10">
		<div class="max-w-4xl mx-auto px-6 py-5">
			<div class="flex items-center justify-between">
				<h1 class="text-[22px] font-semibold text-[#1d1d1f]">
					<i class="fa-solid fa-chart-simple mr-2 text-[#007aff]"></i>
					ダッシュボード
				</h1>
				<a href="/" class="nav-link">
					<i class="fa-solid fa-arrow-left mr-1.5"></i>
					検索に戻る
				</a>
			</div>
		</div>
	</header>

	<main class="max-w-4xl mx-auto px-6 py-6">
		{#if error}
			<div class="alert alert-error mb-5">
				<i class="fa-solid fa-circle-exclamation mr-2"></i>
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
			<div class="flex justify-center py-16">
				<div class="spinner"></div>
			</div>
		{:else if stats}
			<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
				<div class="stats-card">
					<h2 class="stats-label">
						<i class="fa-solid fa-file mr-1.5"></i>
						総ドキュメント数
					</h2>
					<p class="stats-value">{stats.total_documents}</p>
				</div>

				<div class="stats-card">
					<h2 class="stats-label">
						<i class="fa-solid fa-puzzle-piece mr-1.5"></i>
						総チャンク数
					</h2>
					<p class="stats-value">{stats.total_chunks}</p>
				</div>

				<div class="stats-card">
					<h2 class="stats-label">
						<i class="fa-solid fa-clock mr-1.5"></i>
						最終インデックス
					</h2>
					<p class="text-[16px] font-medium text-[#1d1d1f]">{formatDate(stats.last_indexed_at)}</p>
				</div>
			</div>

			<div class="surface p-6 mb-5">
				<h2 class="text-[17px] font-semibold text-[#1d1d1f] mb-4">
					<i class="fa-solid fa-layer-group mr-2 text-[#007aff]"></i>
					メディアタイプ別
				</h2>

				{#if Object.keys(stats.by_media_type).length > 0}
					<div class="space-y-4">
						{#each Object.entries(stats.by_media_type) as [type, count] (type)}
							<div class="flex items-center justify-between gap-4">
								<div class="flex items-center gap-3 min-w-[120px]">
									<i class="fa-solid {getMediaTypeIcon(type)} text-[#86868b]"></i>
									<span class="text-[14px] text-[#1d1d1f]">{getMediaTypeLabel(type)}</span>
								</div>
								<div class="flex-1 flex items-center gap-3">
									<div class="progress-bar flex-1">
										<div
											class="progress-fill"
											style="width: {Math.min((count / stats.total_documents) * 100, 100)}%"
										></div>
									</div>
									<span class="text-[14px] font-medium text-[#1d1d1f] w-12 text-right">{count}</span>
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<div class="empty-state py-6">
						<i class="fa-regular fa-chart-bar text-2xl mb-2 block"></i>
						<p class="text-[14px]">データがありません</p>
					</div>
				{/if}
			</div>

			{#if recentDocs.length > 0}
				<div class="surface p-6 mb-5">
					<h2 class="text-[17px] font-semibold text-[#1d1d1f] mb-4">
						<i class="fa-solid fa-clock-rotate-left mr-2 text-[#007aff]"></i>
						最近のドキュメント
					</h2>
					<ul class="space-y-2">
						{#each recentDocs as doc (doc.id)}
							<li class="list-item group hover:bg-[rgba(0,122,255,0.04)]">
								<div class="flex items-center gap-3 min-w-0 flex-1">
									<div class="file-icon {getFileIconClass(doc.media_type)}">
										<i class="fa-solid {getMediaTypeIcon(doc.media_type)}"></i>
									</div>
									<div class="min-w-0 flex-1">
										<p class="text-[14px] font-medium text-[#1d1d1f] truncate" title={doc.filename}>{doc.filename}</p>
										<p class="text-[13px] text-[#86868b]">{formatSize(doc.size)} - {formatDate(doc.indexed_at)}</p>
									</div>
								</div>
								<button
									onclick={() => openFile(doc.path)}
									class="btn-primary py-1.5 px-3 text-[13px] opacity-0 group-hover:opacity-100 transition-opacity"
								>
									<i class="fa-solid fa-arrow-up-right-from-square mr-1"></i>
									開く
								</button>
							</li>
						{/each}
					</ul>
				</div>
			{/if}

			<div class="flex justify-center">
				<button
					onclick={loadData}
					class="btn-secondary"
				>
					<i class="fa-solid fa-arrows-rotate mr-2"></i>
					更新
				</button>
			</div>
		{/if}
	</main>
</div>
