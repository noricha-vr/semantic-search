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

<div class="flex gap-3 mb-4">
	<div class="relative flex-1">
		<div class="absolute left-3 top-1/2 -translate-y-1/2 text-[#86868b]">
			<i class="fa-solid fa-folder"></i>
		</div>
		<input
			type="text"
			bind:value={newPath}
			onkeydown={handleKeydown}
			placeholder="パスを入力 (例: ~/Documents)"
			class="input-field w-full pl-10"
			{disabled}
		/>
	</div>
	<button
		onclick={handleSubmit}
		{disabled}
		class="btn-primary"
	>
		<i class="fa-solid fa-plus mr-1.5"></i>
		追加
	</button>
</div>
