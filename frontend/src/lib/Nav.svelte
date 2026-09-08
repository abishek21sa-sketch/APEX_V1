<script lang="ts">
	import { page } from '$app/state';
	import { checkHealth } from '$lib/api';
	import { onMount } from 'svelte';

	const LINKS = [
		{ href: '/', label: 'Overview' },
		{ href: '/optimizer', label: 'Optimizer' },
		{ href: '/evaluate', label: 'Evaluate' },
		{ href: '/robust', label: 'Robust check' },
		{ href: '/saved', label: 'Saved' },
		{ href: '/benchmarks', label: 'Benchmarks' },
		{ href: '/surrogates', label: 'Surrogate Lab' },
		{ href: '/agent', label: 'Agent' },
		{ href: '/methodology', label: 'Methodology' }
	];

	let healthStatus = $state<'checking' | 'ok' | 'unreachable'>('checking');
	let pythonStatus = $state('');

	onMount(async () => {
		try {
			const h = await checkHealth();
			healthStatus = 'ok';
			pythonStatus = h.python_service;
		} catch {
			healthStatus = 'unreachable';
		}
	});
</script>

<header class="topbar">
	<div class="topbar-inner">
		<a class="brand" href="/">
			<span class="brand-mark">APEX</span>
		</a>
		<nav class="nav-links">
			{#each LINKS as link}
				<a href={link.href} class:active={page.url.pathname === link.href}>{link.label}</a>
			{/each}
		</nav>
		<div class="health" class:ok={healthStatus === 'ok'} class:bad={healthStatus === 'unreachable'}>
			<span class="health-dot"></span>
			{#if healthStatus === 'checking'}
				checking&hellip;
			{:else if healthStatus === 'ok'}
				backend online &middot; python {pythonStatus}
			{:else}
				backend unreachable
			{/if}
		</div>
	</div>
</header>

<style>
	.topbar {
		border-bottom: 1px solid var(--seam);
		position: sticky;
		top: 0;
		background: rgba(10, 12, 16, 0.85);
		backdrop-filter: blur(8px);
		z-index: 10;
	}
	.topbar-inner {
		max-width: 1180px;
		margin: 0 auto;
		padding: 0.9rem 1.5rem;
		display: flex;
		align-items: center;
		gap: 1.75rem;
	}
	.brand {
		text-decoration: none;
		flex-shrink: 0;
	}
	.brand-mark {
		font-size: 1.15rem;
		font-weight: 700;
		letter-spacing: 0.08em;
		color: var(--blue);
	}
	.nav-links {
		display: flex;
		gap: 1.4rem;
		flex-wrap: wrap;
		flex: 1;
	}
	.nav-links a {
		color: var(--text-dim);
		text-decoration: none;
		font-size: 0.85rem;
		padding: 0.3rem 0;
		border-bottom: 2px solid transparent;
	}
	.nav-links a:hover {
		color: var(--text);
	}
	.nav-links a.active {
		color: var(--text);
		border-bottom-color: var(--blue);
	}
	.health {
		flex-shrink: 0;
	}
	@media (max-width: 720px) {
		.topbar-inner {
			flex-wrap: wrap;
		}
		.health {
			order: 3;
			width: 100%;
		}
	}
</style>
