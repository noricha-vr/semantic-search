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
	<div class="alert alert-info mb-5">
		<div class="flex items-center gap-4">
			<div class="spinner"></div>
			<div>
				<p class="font-semibold text-[15px]">
					<i class="fa-solid fa-rotate mr-2"></i>
					インデックス処理中...
				</p>
				<p class="text-[14px] opacity-90 mt-1">{indexingPath}</p>
				<p class="text-[13px] opacity-75 mt-1">
					PDF VLM処理がある場合、数分かかることがあります
				</p>
			</div>
		</div>
	</div>
{/if}
