<script lang="ts">
	/**
	 * パス入力とインデックスボタンを含むフォームコンポーネント
	 */

	interface Props {
		disabled?: boolean;
		onAddPath: (path: string) => void;
	}

	let { disabled = false, onAddPath }: Props = $props();
	let newPath = $state('');

	function handleSubmit() {
		if (!newPath.trim() || disabled) return;
		onAddPath(newPath.trim());
		newPath = '';
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			handleSubmit();
		}
	}
</script>

<div class="flex gap-2 mb-4">
	<input
		type="text"
		bind:value={newPath}
		onkeydown={handleKeydown}
		placeholder="パスを入力 (例: ~/Documents)"
		class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
		{disabled}
	/>
	<button
		onclick={handleSubmit}
		{disabled}
		class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
	>
		追加
	</button>
</div>
