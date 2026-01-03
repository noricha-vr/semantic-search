<script lang="ts">
	/**
	 * インデックス処理中の状態を表示するコンポーネント
	 */

	interface Props {
		isIndexing: boolean;
		indexingPath: string;
	}

	let { isIndexing, indexingPath }: Props = $props();
</script>

{#if isIndexing}
	<div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
		<div class="flex items-center gap-3">
			<div class="animate-spin rounded-full h-5 w-5 border-2 border-blue-500 border-t-transparent"></div>
			<div>
				<p class="font-medium text-blue-800">インデックス処理中...</p>
				<p class="text-sm text-blue-600">{indexingPath}</p>
				<p class="text-sm text-blue-500 mt-1">
					PDF VLM処理がある場合、数分かかることがあります
				</p>
			</div>
		</div>
	</div>
{/if}
