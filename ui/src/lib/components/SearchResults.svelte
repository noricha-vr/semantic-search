<script lang="ts">
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

	interface Props {
		results: SearchResult[];
		onOpen: (result: SearchResult) => void;
		onReveal: (result: SearchResult) => void;
	}

	let { results, onOpen, onReveal }: Props = $props();

	function formatTimestamp(seconds?: number): string {
		if (seconds === undefined || seconds === null) return '';
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	}

	function getMediaTypeIcon(mediaType: string): string {
		switch (mediaType) {
			case 'image':
				return 'fa-image';
			case 'video':
				return 'fa-video';
			case 'audio':
				return 'fa-music';
			case 'document':
			default:
				return 'fa-file-alt';
		}
	}

	function getMediaTypeLabel(mediaType: string): string {
		switch (mediaType) {
			case 'image':
				return '画像';
			case 'video':
				return '動画';
			case 'audio':
				return '音声';
			case 'document':
			default:
				return 'ドキュメント';
		}
	}
</script>

<div class="space-y-4">
	{#each results as result (result.chunk_id)}
		<div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
			<div class="p-4">
				<div class="flex items-start justify-between gap-4">
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2 mb-2">
							<span class="inline-flex items-center px-2 py-0.5 rounded text-sm font-medium bg-gray-100 text-gray-700">
								<i class="fa {getMediaTypeIcon(result.media_type)} mr-1"></i>
								{getMediaTypeLabel(result.media_type)}
							</span>
							{#if result.start_time !== undefined && result.start_time !== null}
								<span class="text-sm text-blue-600">
									{formatTimestamp(result.start_time)}
									{#if result.end_time !== undefined && result.end_time !== null}
										- {formatTimestamp(result.end_time)}
									{/if}
								</span>
							{/if}
							<span class="text-sm text-gray-400">
								スコア: {result.score.toFixed(3)}
							</span>
						</div>

						<h3 class="text-base font-medium text-gray-900 truncate mb-1">
							{result.filename}
						</h3>

						<p class="text-sm text-gray-600 line-clamp-3">
							{result.text}
						</p>

						<p class="text-sm text-gray-400 truncate mt-2" title={result.path}>
							{result.path}
						</p>
					</div>

					<div class="flex flex-col gap-2">
						<button
							onclick={() => onOpen(result)}
							class="px-3 py-1.5 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors whitespace-nowrap"
						>
							開く
						</button>
						<button
							onclick={() => onReveal(result)}
							class="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors whitespace-nowrap"
						>
							Finder
						</button>
					</div>
				</div>
			</div>
		</div>
	{/each}
</div>

<style>
	.line-clamp-3 {
		display: -webkit-box;
		-webkit-line-clamp: 3;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
