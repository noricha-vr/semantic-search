<script lang="ts">
	let watchPaths = $state<string[]>([]);
	let newPath = $state('');
	let message = $state('');

	async function addPath() {
		if (!newPath.trim()) return;

		watchPaths = [...watchPaths, newPath.trim()];
		newPath = '';
		message = 'パスを追加しました';
		setTimeout(() => (message = ''), 3000);
	}

	function removePath(index: number) {
		watchPaths = watchPaths.filter((_, i) => i !== index);
	}

	async function indexPath(path: string) {
		message = 'インデックス化を開始しました...';

		try {
			const response = await fetch('http://localhost:8765/api/documents/index', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ path, recursive: true })
			});

			if (!response.ok) {
				throw new Error('インデックス化に失敗しました');
			}

			const data = await response.json();
			message = `${data.indexed_count}件のファイルをインデックス化しました`;
		} catch (error) {
			message = error instanceof Error ? error.message : 'エラーが発生しました';
		}
	}
</script>

<div class="min-h-screen bg-gray-50">
	<header class="bg-white shadow-sm border-b border-gray-200">
		<div class="max-w-4xl mx-auto px-4 py-6">
			<div class="flex items-center justify-between">
				<h1 class="text-2xl font-bold text-gray-900">設定</h1>
				<a href="/" class="text-blue-500 hover:text-blue-600">検索に戻る</a>
			</div>
		</div>
	</header>

	<main class="max-w-4xl mx-auto px-4 py-6">
		{#if message}
			<div class="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded mb-6">
				{message}
			</div>
		{/if}

		<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
			<h2 class="text-lg font-semibold text-gray-900 mb-4">監視パス</h2>

			<div class="flex gap-2 mb-4">
				<input
					type="text"
					bind:value={newPath}
					placeholder="パスを入力 (例: ~/Documents)"
					class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
				/>
				<button
					onclick={addPath}
					class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
				>
					追加
				</button>
			</div>

			{#if watchPaths.length > 0}
				<ul class="space-y-2">
					{#each watchPaths as path, i (i)}
						<li class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
							<span class="text-gray-700">{path}</span>
							<div class="flex gap-2">
								<button
									onclick={() => indexPath(path)}
									class="px-3 py-1 text-sm bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
								>
									インデックス
								</button>
								<button
									onclick={() => removePath(i)}
									class="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors"
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
		</div>

		<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
			<h2 class="text-lg font-semibold text-gray-900 mb-4">クイックインデックス</h2>
			<p class="text-gray-600 mb-4">
				よく使うパスをすばやくインデックス化できます
			</p>

			<div class="grid grid-cols-2 gap-2">
				<button
					onclick={() => indexPath('~/Documents')}
					class="p-3 text-left bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
				>
					<span class="font-medium">Documents</span>
					<span class="block text-sm text-gray-500">~/Documents</span>
				</button>
				<button
					onclick={() => indexPath('~/Desktop')}
					class="p-3 text-left bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
				>
					<span class="font-medium">Desktop</span>
					<span class="block text-sm text-gray-500">~/Desktop</span>
				</button>
				<button
					onclick={() => indexPath('~/Downloads')}
					class="p-3 text-left bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
				>
					<span class="font-medium">Downloads</span>
					<span class="block text-sm text-gray-500">~/Downloads</span>
				</button>
				<button
					onclick={() => indexPath('~/Pictures')}
					class="p-3 text-left bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
				>
					<span class="font-medium">Pictures</span>
					<span class="block text-sm text-gray-500">~/Pictures</span>
				</button>
			</div>
		</div>
	</main>
</div>
