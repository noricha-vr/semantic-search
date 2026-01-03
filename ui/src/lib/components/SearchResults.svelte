<script lang="ts">
	import { getMediaTypeLabel, getMediaTypeIcon } from '$lib/utils/mediaType';

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
		query: string;
		onOpen: (result: SearchResult) => void;
		onReveal: (result: SearchResult) => void;
	}

	let { results, query, onOpen, onReveal }: Props = $props();

	function highlightText(text: string, searchQuery: string): string {
		if (!searchQuery.trim()) return escapeHtml(text);

		const escapedText = escapeHtml(text);
		const words = searchQuery.trim().split(/\s+/).filter((w) => w.length > 0);
		if (words.length === 0) return escapedText;

		const pattern = words.map((w) => escapeRegex(w)).join('|');
		const regex = new RegExp(`(${pattern})`, 'gi');

		return escapedText.replace(regex, '<mark class="highlight">$1</mark>');
	}

	function escapeHtml(text: string): string {
		return text
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/"/g, '&quot;')
			.replace(/'/g, '&#039;');
	}

	function escapeRegex(text: string): string {
		return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
	}

	function formatTimestamp(seconds?: number): string {
		if (seconds === undefined || seconds === null) return '';
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	}

	function getFileIconClass(mediaType: string): string {
		const iconClasses: Record<string, string> = {
			document: 'file-icon-document',
			image: 'file-icon-image',
			video: 'file-icon-video',
			audio: 'file-icon-audio',
			pdf: 'file-icon-document',
			text: 'file-icon-document'
		};
		return iconClasses[mediaType] || 'file-icon-document';
	}
</script>

<div class="space-y-3">
	{#each results as result (result.chunk_id)}
		<div class="result-item group">
			<div class="file-icon {getFileIconClass(result.media_type)}">
				<i class="fa-solid {getMediaTypeIcon(result.media_type)}"></i>
			</div>

			<div class="flex-1 min-w-0">
				<div class="flex items-center gap-2 mb-1">
					<h3 class="text-[15px] font-semibold text-[#1d1d1f] truncate">
						{result.filename}
					</h3>
					{#if result.start_time !== undefined && result.start_time !== null}
						<span class="badge badge-accent">
							<i class="fa-solid fa-clock mr-1"></i>
							{formatTimestamp(result.start_time)}
							{#if result.end_time !== undefined && result.end_time !== null}
								- {formatTimestamp(result.end_time)}
							{/if}
						</span>
					{/if}
				</div>

				<p class="text-[14px] text-[#1d1d1f] line-clamp-2 mb-2">
					{@html highlightText(result.text, query)}
				</p>

				<div class="flex items-center gap-3">
					<span class="text-[13px] text-[#86868b] truncate flex-1" title={result.path}>
						<i class="fa-solid fa-folder mr-1"></i>
						{result.path}
					</span>
					<span class="badge badge-gray">
						{getMediaTypeLabel(result.media_type)}
					</span>
					<span class="text-[13px] text-[#86868b]">
						{result.score.toFixed(2)}
					</span>
				</div>
			</div>

			<div class="result-actions flex flex-col gap-2 ml-2">
				<button
					onclick={() => onOpen(result)}
					class="btn-primary py-1.5 px-3 text-[13px]"
					title="ファイルを開く"
				>
					<i class="fa-solid fa-arrow-up-right-from-square mr-1"></i>
					開く
				</button>
				<button
					onclick={() => onReveal(result)}
					class="btn-secondary py-1.5 px-3 text-[13px]"
					title="Finderで表示"
				>
					<i class="fa-brands fa-apple mr-1"></i>
					Finder
				</button>
			</div>
		</div>
	{/each}
</div>
