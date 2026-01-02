<script lang="ts">
	interface Props {
		onSearch: (query: string, mediaType: string | null) => void;
		isLoading?: boolean;
	}

	let { onSearch, isLoading = false }: Props = $props();

	let inputValue = $state('');
	let selectedMediaType = $state<string | null>(null);

	const mediaTypes = [
		{ value: null, label: 'すべて' },
		{ value: 'document', label: 'ドキュメント' },
		{ value: 'image', label: '画像' },
		{ value: 'audio', label: '音声' },
		{ value: 'video', label: '動画' }
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

<div class="space-y-3">
	<form onsubmit={handleSubmit} class="relative">
		<input
			type="text"
			bind:value={inputValue}
			onkeydown={handleKeyDown}
			placeholder="検索キーワードを入力..."
			disabled={isLoading}
			class="w-full px-4 py-3 pr-12 text-base border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
		/>
		<button
			type="submit"
			disabled={isLoading || !inputValue.trim()}
			class="absolute right-2 top-1/2 transform -translate-y-1/2 px-3 py-1.5 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
		>
			{#if isLoading}
				<span class="inline-block animate-spin">...</span>
			{:else}
				検索
			{/if}
		</button>
	</form>

	<div class="flex gap-2 flex-wrap">
		{#each mediaTypes as { value, label }}
			<button
				type="button"
				onclick={() => handleMediaTypeChange(value)}
				class="px-3 py-1 text-sm rounded-full transition-colors {selectedMediaType === value
					? 'bg-blue-500 text-white'
					: 'bg-gray-100 text-gray-700 hover:bg-gray-200'}"
			>
				{label}
			</button>
		{/each}
	</div>
</div>
