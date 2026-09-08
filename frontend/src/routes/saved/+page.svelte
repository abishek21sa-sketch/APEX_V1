<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import Chart from 'chart.js/auto';
	import { fetchBenchmarkVehicles, type BenchmarkVehicle } from '$lib/api';
	import { getSavedDesigns, removeSavedDesign, type SavedDesign } from '$lib/savedDesigns';

	const MSRP_MARKUP_FACTOR = 1.4;

	let designs = $state<SavedDesign[]>([]);
	let benchmarkVehicles = $state<BenchmarkVehicle[]>([]);

	onMount(async () => {
		designs = getSavedDesigns();
		try {
			benchmarkVehicles = await fetchBenchmarkVehicles();
		} catch {
			// Non-critical -- the comparison table still works without the market overlay.
		}
	});

	function remove(id: string) {
		removeSavedDesign(id);
		designs = getSavedDesigns();
	}

	function reEvaluate(design: SavedDesign) {
		sessionStorage.setItem('apex_inspect_candidate', JSON.stringify(design.candidate));
		goto('/evaluate');
	}

	let chartCanvas = $state<HTMLCanvasElement | null>(null);

	$effect(() => {
		const canvas = chartCanvas;
		const saved = designs;
		const market = benchmarkVehicles;
		if (!canvas || saved.length === 0) return;

		const datasets = [
			...(market.length > 0
				? [
						{
							label: 'real production EVs',
							data: market.map((v) => ({ x: v.msrp_usd, y: v.epa_range_mi })),
							backgroundColor: 'rgba(139, 147, 163, 0.4)',
							borderColor: '#8b93a3',
							pointRadius: 3
						}
					]
				: []),
			{
				label: 'your saved designs',
				data: saved.map((d) => ({
					x: d.result.manufacturing_cost_usd * MSRP_MARKUP_FACTOR,
					y: d.result.range_mi
				})),
				backgroundColor: 'rgba(79, 140, 247, 0.85)',
				borderColor: '#4f8cf7',
				pointRadius: 6
			}
		];

		const instance = new Chart(canvas, {
			type: 'scatter',
			data: { datasets },
			options: {
				responsive: true,
				maintainAspectRatio: false,
				animation: false,
				plugins: {
					legend: { display: false },
					tooltip: {
						callbacks: {
							label: (ctx) => {
								if (ctx.datasetIndex === 0 && market.length > 0) {
									const v = market[ctx.dataIndex];
									return `${v.name}: $${v.msrp_usd.toLocaleString()}, ${v.epa_range_mi}mi`;
								}
								const d = saved[ctx.dataIndex];
								return `${d.label}: ~$${(d.result.manufacturing_cost_usd * MSRP_MARKUP_FACTOR).toLocaleString(undefined, { maximumFractionDigits: 0 })} est. MSRP, ${d.result.range_mi.toFixed(0)}mi`;
							}
						}
					}
				},
				scales: {
					x: {
						title: { display: true, text: 'estimated MSRP ($)', color: '#8b93a3' },
						ticks: { color: '#5b6272' },
						grid: { color: '#1c212a' }
					},
					y: {
						title: { display: true, text: 'range (mi)', color: '#8b93a3' },
						ticks: { color: '#5b6272' },
						grid: { color: '#1c212a' }
					}
				}
			}
		});

		return () => instance.destroy();
	});
</script>

<svelte:head>
	<title>Saved designs — APEX</title>
</svelte:head>

<div class="shell">
	<header class="page-header">
		<p class="eyebrow">Your portfolio</p>
		<h1 class="page-title">Saved designs</h1>
		<p class="page-subtitle">
			Designs saved from the Evaluate page, kept in this browser only -- no account or server-side
			storage. Compare them side by side, or against each other and the real market.
		</p>
	</header>

	{#if designs.length === 0}
		<div class="empty-state">
			<p>No saved designs yet.</p>
			<p class="hint">
				Evaluate a candidate on the <a href="/evaluate">Evaluate page</a> and hit "save design" to
				start building a comparison set.
			</p>
		</div>
	{:else}
		<section class="panel" style="margin-bottom: 1.25rem;">
			<p class="chart-caption">
				estimated MSRP vs range &mdash; your {designs.length} saved design{designs.length === 1
					? ''
					: 's'}{benchmarkVehicles.length > 0 ? ` against ${benchmarkVehicles.length} real production EVs` : ''}
			</p>
			<div class="chart-wrap">
				<!-- svelte-ignore a11y_no_interactive_element_to_noninteractive_role -->
				<canvas
					bind:this={chartCanvas}
					role="img"
					aria-label="Scatter chart comparing your saved designs against real production EVs on estimated MSRP vs range"
				></canvas>
			</div>
		</section>

		<section class="panel">
			<div class="table-wrap">
				<table class="results">
					<thead>
						<tr>
							<th>label</th><th>battery</th><th>motor</th><th>mass</th><th>cost</th><th>0-60</th
							><th>range</th><th>saved</th><th></th>
						</tr>
					</thead>
					<tbody>
						{#each designs as d}
							<tr>
								<td>{d.label}</td>
								<td>{d.candidate.battery_capacity_kwh.toFixed(0)}kWh</td>
								<td>{d.candidate.motor_power_kw.toFixed(0)}kW</td>
								<td>{d.result.mass_kg.toFixed(0)}kg</td>
								<td>${d.result.manufacturing_cost_usd.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
								<td>{d.result.zero_to_sixty_s.toFixed(1)}s</td>
								<td>{d.result.range_mi.toFixed(0)}mi</td>
								<td>{new Date(d.savedAt).toLocaleDateString()}</td>
								<td>
									<button class="link-btn" onclick={() => reEvaluate(d)}>open</button>
									<button class="link-btn" onclick={() => remove(d.id)}>remove</button>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</section>
	{/if}
</div>

<style>
	.chart-caption {
		font-size: 0.78rem;
		color: var(--text-dim);
		margin: 0 0 0.75rem;
	}
	.chart-wrap {
		position: relative;
		width: 100%;
		height: 340px;
	}
	.results .link-btn {
		margin-right: 0.75rem;
	}
</style>
