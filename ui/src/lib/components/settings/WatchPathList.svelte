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
			<li class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
				<span class="text-gray-700">{path}</span>
				<div class="flex gap-2">
					<button
						onclick={() => onIndex(path)}
						disabled={isIndexing}
						class="px-3 py-1 text-sm bg-green-500 text-white rounded hover:bg-green-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
					>
						{isIndexing && indexingPath === path ? '処理中...' : 'インデックス'}
					</button>
					<button
						onclick={() => onRemove(i)}
						disabled={isIndexing}
						class="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
					>
						削除
					</button>
				</div>
			</li>
		{/each}
	</ul>
{:else}
	<p class="text-gray-500 text-center py-4">監視パスが設定されていません</p>
{/if}
