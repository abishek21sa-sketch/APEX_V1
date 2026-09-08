<script lang="ts">
	import { page } from '$app/state';
</script>

<svelte:head>
	<title>{page.status} — APEX</title>
</svelte:head>

<div class="shell">
	<div class="error-block">
		<p class="eyebrow">Error {page.status}</p>
		<h1 class="page-title">{page.error?.message ?? 'Something went wrong'}</h1>
		<p class="page-subtitle">
			{#if page.status === 404}
				There's nothing at this address. Try one of the pages in the nav above, or head back to
				the <a href="/">overview</a>.
			{:else}
				The backend may be unreachable, or something failed unexpectedly. Check that
				<code>docker compose up</code> (or the dev servers) are actually running, then try again.
			{/if}
		</p>
	</div>
</div>

<style>
	.error-block {
		padding: 4rem 0;
		max-width: 42em;
	}
</style>
