<script lang="ts">
	import { onMount } from 'svelte';
	import {
		fetchSurrogateComparison,
		type SurrogateComparisonResponse
	} from '$lib/api';

	let result = $state<SurrogateComparisonResponse | null>(null);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let nSamples = $state(80);
	let seed = $state(7);

	async function runComparison() {
		loading = true;
		error = null;
		try {
			result = await fetchSurrogateComparison(nSamples, seed);
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	}

	onMount(runComparison);
</script>

<svelte:head>
	<title>Surrogate Lab — APEX</title>
</svelte:head>

<div class="shell">
	<header class="page-header">
		<p class="eyebrow">Evidence workspace</p>
		<h1 class="page-title">Surrogate Lab</h1>
		<p class="page-subtitle">
			Compare Gaussian Process and Random Forest surrogates against APEX's first-principles
			physics outputs before using either model for search or active learning.
		</p>
	</header>

	<section class="panel controls">
		<label>physics samples <input type="number" min="40" max="220" step="10" bind:value={nSamples} /></label>
		<label>seed <input type="number" min="0" step="1" bind:value={seed} /></label>
		<button class="primary-btn" onclick={runComparison} disabled={loading}>
			{loading ? 'training…' : 'run comparison'}
		</button>
	</section>

	{#if error}
		<p class="page-error">{error}</p>
	{:else if loading && !result}
		<p class="hint">Generating physics-backed training data and fitting both models…</p>
	{:else if result}
		<section class="panel">
			<div class="section-head">
				<div>
					<p class="eyebrow">{result.dataset}</p>
					<h2>Model review</h2>
				</div>
				<span class="run-stamp">n={result.n_samples} · seed={result.seed}</span>
			</div>
			<div class="table-wrap">
				<table class="results">
					<thead><tr><th>target</th><th>Gaussian Process</th><th>Random Forest</th><th>exploration pick</th></tr></thead>
					<tbody>
						{#each result.comparison as row}
							<tr>
								<td><strong>{row.target}</strong></td>
								<td>R² {row.gaussian_process.r2.toFixed(3)} · RMSE {row.gaussian_process.rmse.toFixed(3)} · MAE {row.gaussian_process.mae.toFixed(3)}</td>
								<td>R² {row.random_forest.r2.toFixed(3)} · RMSE {row.random_forest.rmse.toFixed(3)} · MAE {row.random_forest.mae.toFixed(3)}</td>
								<td class="pick">{row.selected_for_exploration.replace('_', ' ')}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</section>

		<section class="evidence-grid">
			<div class="evidence-card"><span>selection policy</span><strong>{result.selection_policy}</strong></div>
			<div class="evidence-card"><span>claim boundary</span><strong>{result.claim_boundary}</strong></div>
		</section>
	{/if}
</div>

<style>
	.controls { display: flex; align-items: end; gap: 1rem; flex-wrap: wrap; }
	.controls label { display: grid; gap: .35rem; color: var(--text-dim); font-size: .78rem; }
	.controls input { width: 110px; }
	.section-head { display:flex; justify-content:space-between; align-items:baseline; gap:1rem; border-bottom:1px solid var(--seam); padding-bottom:.75rem; margin-bottom:1rem; }
	.section-head h2 { margin:0; }
	.run-stamp { color:var(--text-dim); font: .75rem var(--font-mono); }
	.table-wrap { overflow:auto; }
	.results { width:100%; border-collapse:collapse; font-size:.8rem; }
	.results th, .results td { padding:.85rem .75rem; border-bottom:1px solid var(--seam); text-align:left; vertical-align:top; }
	.results th { color:var(--text-dim); font-size:.72rem; text-transform:uppercase; letter-spacing:.06em; }
	.pick { color:var(--cyan); font-weight:700; white-space:nowrap; }
	.evidence-grid { display:grid; grid-template-columns:repeat(2, 1fr); gap:1rem; margin-top:1rem; }
	.evidence-card { background:var(--panel); border:1px solid var(--seam); border-radius:12px; padding:1.1rem 1.2rem; display:grid; gap:.45rem; }
	.evidence-card span { color:var(--text-dim); font-size:.7rem; text-transform:uppercase; letter-spacing:.08em; }
	.evidence-card strong { font-size:.82rem; line-height:1.5; }
	@media (max-width:720px) { .evidence-grid { grid-template-columns:1fr; } }
</style>
