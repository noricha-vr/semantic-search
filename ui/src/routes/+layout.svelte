<script lang="ts">
	import '../app.css';

	let { children } = $props();
</script>

<svelte:head>
	<title>LocalDocSearch</title>
	<meta name="description" content="ローカルドキュメント検索システム" />
</svelte:head>

{@render children()}
