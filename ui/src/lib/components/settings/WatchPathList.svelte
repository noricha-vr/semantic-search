<script lang="ts">
	/**
	 * 監視パス一覧を表示するコンポーネント
	 */

	interface Props {
		watchPaths: string[];
		isIndexing: boolean;
		indexingPath: string;
		onIndex: (path: string) => void;
		onRemove: (index: number) => void;
	}

	let { watchPaths, isIndexing, indexingPath, onIndex, onRemove }: Props = $props();
</script>

{#if watchPaths.length > 0}
	<ul class="space-y-2">
		{#each watchPaths as path, i (i)}
			<li class="list-item group">
				<div class="flex items-center gap-3">
					<i class="fa-solid fa-folder text-[#ff9500]"></i>
					<span class="text-[14px] text-[#1d1d1f]">{path}</span>
				</div>
				<div class="flex gap-2">
					<button
						onclick={() => onIndex(path)}
						disabled={isIndexing}
						class="btn-primary py-1.5 px-3 text-[13px]"
					>
						{#if isIndexing && indexingPath === path}
							<i class="fa-solid fa-spinner fa-spin mr-1.5"></i>
							処理中...
						{:else}
							<i class="fa-solid fa-database mr-1.5"></i>
							インデックス
						{/if}
					</button>
					<button
						onclick={() => onRemove(i)}
						disabled={isIndexing}
						class="btn-secondary py-1.5 px-3 text-[13px] text-[#ff3b30] hover:bg-[rgba(255,59,48,0.1)]"
					>
						<i class="fa-solid fa-trash-can mr-1.5"></i>
						削除
					</button>
				</div>
			</li>
		{/each}
	</ul>
{:else}
	<div class="empty-state py-6">
		<i class="fa-regular fa-folder text-2xl mb-2 block"></i>
		<p class="text-[14px]">監視パスが設定されていません</p>
	</div>
{/if}
