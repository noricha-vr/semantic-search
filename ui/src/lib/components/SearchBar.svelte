<script lang="ts">
	interface Props {
		onSearch: (query: string, mediaType: string | null) => void;
		isLoading?: boolean;
	}

	let { onSearch, isLoading = false }: Props = $props();

	let inputValue = $state('');
	let selectedMediaType = $state<string | null>(null);

	const mediaTypes = [
		{ value: null, label: 'すべて', icon: 'fa-layer-group' },
		{ value: 'document', label: 'ドキュメント', icon: 'fa-file-alt' },
		{ value: 'image', label: '画像', icon: 'fa-image' },
		{ value: 'audio', label: '音声', icon: 'fa-music' },
		{ value: 'video', label: '動画', icon: 'fa-video' }
	];

	function handleSubmit(event: Event) {
		event.preventDefault();
		onSearch(inputValue, selectedMediaType);
	}

	function handleKeyDown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			onSearch(inputValue, selectedMediaType);
		}
	}

	function handleMediaTypeChange(mediaType: string | null) {
		selectedMediaType = mediaType;
		if (inputValue.trim()) {
			onSearch(inputValue, mediaType);
		}
	}
</script>

<div class="space-y-4">
	<form onsubmit={handleSubmit} class="relative">
		<div class="absolute left-4 top-1/2 -translate-y-1/2 text-[#86868b]">
			<i class="fa-solid fa-magnifying-glass text-lg"></i>
		</div>
		<input
			type="text"
			bind:value={inputValue}
			onkeydown={handleKeyDown}
			placeholder="ドキュメントを検索..."
			disabled={isLoading}
			class="search-input"
		/>
		{#if isLoading}
			<div class="absolute right-4 top-1/2 -translate-y-1/2">
				<div class="spinner"></div>
			</div>
		{:else if inputValue.trim()}
			<button
				type="submit"
				class="absolute right-3 top-1/2 -translate-y-1/2 btn-primary py-2 px-4"
				title="検索を実行"
			>
				<i class="fa-solid fa-arrow-right"></i>
			</button>
		{/if}
	</form>

	<div class="segment-control">
		{#each mediaTypes as { value, label, icon }}
			<button
				type="button"
				onclick={() => handleMediaTypeChange(value)}
				class="segment-control-item {selectedMediaType === value ? 'active' : ''}"
			>
				<i class="fa-solid {icon} mr-1.5"></i>
				{label}
			</button>
		{/each}
	</div>
</div>
