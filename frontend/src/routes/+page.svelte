<script lang="ts">
	const STATS = [
		{ value: '10', label: 'build phases' },
		{ value: '238', label: 'tests passing' },
		{ value: 'NSGA2', label: 'real multi-objective search' },
		{ value: '98', label: 'real 2026 EVs benchmarked' }
	];

	const FEATURES = [
		{
			title: 'First-principles physics',
			body: 'Road-load equation, tractive-force limits, a battery equivalent-circuit model, and a speed/torque-aware motor efficiency map. No learned surrogate stands in for the physics when scoring a design.'
		},
		{
			title: 'Real multi-objective optimization',
			body: 'A genuine NSGA2 Pareto search over a mixed continuous/discrete design space — cost, mass, 0-60, and range traded off against each other, not collapsed into one invented priority number.'
		},
		{
			title: 'Robust under uncertainty',
			body: 'Monte Carlo scenario sampling across payload, temperature, road grade, tire wear, and battery aging, with a chance-constrained feasibility check — a design that looks good on paper still has to hold up in realistic conditions.'
		},
		{
			title: 'An agent with real tools, not a free hand',
			body: 'Claude Opus 5 restricted to seven of this platform’s own query and optimization functions — the same design-space, evaluate, Pareto search, and robust-check calls the UI itself makes, nothing invented.'
		},
		{
			title: 'Checked against the real market',
			body: '98 currently-shipping production EVs — real published price and EPA range, not simulated — plotted against every search result, so a design isn’t just Pareto-optimal in isolation, it’s positioned against what a buyer could purchase today.'
		}
	];

	const TIERS = [
		{
			name: 'Python scientific service',
			role: 'Runs the physics kernel, the optimizer, the robust checker, and the agent’s tools. Synchronous by design — its whole job is compute-and-return.'
		},
		{
			name: 'Rust orchestration backend',
			role: 'Routes requests, runs the slow Pareto search as a background job with polling so the browser never blocks, and proxies everything else straight through.'
		},
		{
			name: 'SvelteKit workstation',
			role: 'The engineering interface itself — mission builder, optimizer results, single-candidate evaluation, and the agent chat, all against the live backend.'
		}
	];
</script>

<svelte:head>
	<title>APEX — Vehicle Architecture &amp; Engineering Optimization Platform</title>
</svelte:head>

<div class="shell">
	<section class="hero">
		<p class="eyebrow">Vehicle architecture &amp; engineering optimization</p>
		<h1 class="hero-title">APEX</h1>
		<p class="hero-subtitle">
			Given performance, range, packaging, cost, and regulatory requirements, APEX recommends
			Pareto-optimal EV architectures — battery, motor, gearing, aero, mass — using real
			operations-research and physics-based simulation, not an invented composite score.
		</p>
		<div class="hero-actions">
			<a class="primary-btn" href="/optimizer">Open the optimizer</a>
			<a class="ghost-btn" href="/methodology">Read the methodology</a>
		</div>
	</section>

	<div class="stat-row">
		{#each STATS as stat, i}
			<div class="stat-tile" style="animation-delay: {i * 0.08}s">
				<p class="stat-value">{stat.value}</p>
				<p class="stat-label">{stat.label}</p>
			</div>
		{/each}
	</div>

	<section class="section">
		<div class="section-head">
			<h2>What makes this real</h2>
		</div>
		<div class="feature-grid">
			{#each FEATURES as f}
				<div class="feature-card">
					<h3>{f.title}</h3>
					<p>{f.body}</p>
				</div>
			{/each}
		</div>
	</section>

	<section class="section">
		<div class="section-head">
			<h2>Three tiers, one live system</h2>
			<a class="link-btn" href="/methodology">full methodology &rarr;</a>
		</div>
		<div class="tier-row">
			{#each TIERS as tier, i}
				<div class="tier-card">
					<span class="tier-index">{i + 1}</span>
					<h3>{tier.name}</h3>
					<p>{tier.role}</p>
				</div>
			{/each}
		</div>
	</section>
</div>

<style>
	.hero {
		padding: 4rem 0 2.5rem;
	}
	.hero-title {
		font-size: clamp(2.6rem, 7vw, 4rem);
		font-weight: 700;
		letter-spacing: -0.01em;
		margin: 0 0 1rem;
		color: var(--text);
	}
	.hero-subtitle {
		color: var(--text-dim);
		font-size: 1.05rem;
		line-height: 1.7;
		max-width: 42em;
		margin: 0 0 1.75rem;
	}
	.hero-actions {
		display: flex;
		gap: 0.9rem;
	}
	.hero-actions .primary-btn,
	.hero-actions .ghost-btn {
		text-decoration: none;
		display: inline-flex;
		align-items: center;
	}

	.stat-row {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 1px;
		background: var(--seam);
		border: 1px solid var(--seam);
		border-radius: 10px;
		overflow: hidden;
		margin-bottom: 3.5rem;
	}
	@media (max-width: 720px) {
		.stat-row {
			grid-template-columns: repeat(2, 1fr);
		}
	}
	.stat-tile {
		background: var(--panel);
		padding: 1.4rem 1.25rem;
		animation: stat-in 0.5s ease-out backwards;
	}
	@keyframes stat-in {
		0% {
			opacity: 0;
			transform: translateY(6px);
		}
		100% {
			opacity: 1;
			transform: translateY(0);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.stat-tile {
			animation: none;
		}
	}
	.stat-value {
		font-family: var(--font-mono);
		font-size: clamp(1.2rem, 2.6vw, 1.6rem);
		font-weight: 600;
		color: var(--cyan);
		margin: 0 0 0.4rem;
	}
	.stat-label {
		font-size: 0.78rem;
		color: var(--text-dim);
		margin: 0;
	}

	.section {
		margin-bottom: 3.5rem;
	}
	.section-head {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		border-bottom: 1px solid var(--seam);
		padding-bottom: 0.6rem;
		margin-bottom: 1.25rem;
		flex-wrap: wrap;
		gap: 0.4rem;
	}
	.section-head h2 {
		font-size: 1.1rem;
		font-weight: 600;
		margin: 0;
	}

	.feature-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
		gap: 1rem;
	}
	.feature-card {
		background: var(--panel);
		border: 1px solid var(--seam);
		border-radius: 12px;
		padding: 1.3rem 1.4rem;
	}
	.feature-card h3 {
		font-size: 0.95rem;
		font-weight: 600;
		margin: 0 0 0.5rem;
		color: var(--cyan);
	}
	.feature-card p {
		font-size: 0.85rem;
		line-height: 1.6;
		color: var(--text-dim);
		margin: 0;
	}

	.tier-row {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 1rem;
	}
	@media (max-width: 900px) {
		.tier-row {
			grid-template-columns: 1fr;
		}
	}
	.tier-card {
		background: var(--panel);
		border: 1px solid var(--seam);
		border-radius: 12px;
		padding: 1.3rem 1.4rem;
		position: relative;
	}
	.tier-index {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		border-radius: 6px;
		background: var(--amber-soft);
		color: var(--amber);
		font-size: 0.78rem;
		font-weight: 700;
		margin-bottom: 0.7rem;
	}
	.tier-card h3 {
		font-size: 0.92rem;
		font-weight: 600;
		margin: 0 0 0.4rem;
	}
	.tier-card p {
		font-size: 0.83rem;
		line-height: 1.55;
		color: var(--text-dim);
		margin: 0;
	}
</style>
