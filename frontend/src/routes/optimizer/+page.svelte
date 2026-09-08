<script lang="ts">
	import { onMount } from 'svelte';
	import Chart from 'chart.js/auto';
	import {
		fetchBenchmarkVehicles,
		fetchRequirementKinds,
		pollParetoJob,
		startParetoJob,
		type BenchmarkVehicle,
		type ParetoPoint,
		type RequirementSpec
	} from '$lib/api';
	import { goto } from '$app/navigation';

	// Same manufacturing-cost -> MSRP markup used elsewhere in this codebase
	// (see apex.design.constraints.example_crossover_mission) -- our own
	// designs' "manufacturing cost" objective and a real vehicle's MSRP are
	// different quantities; this is what makes comparing them fair rather
	// than apples-to-oranges.
	const MSRP_MARKUP_FACTOR = 1.4;

	let requirementKinds = $state<string[]>([]);
	let metadataError = $state<string | null>(null);
	let benchmarkVehicles = $state<BenchmarkVehicle[]>([]);

	let requirements = $state<RequirementSpec[]>([
		{ kind: 'max_acceleration_time_s', threshold: 6.0 },
		{ kind: 'min_highway_range_mi', threshold: 310.0 },
		{ kind: 'max_manufacturing_cost_usd', threshold: 30000.0 }
	]);
	let popSize = $state(40);
	let nGen = $state(15);
	let seed = $state(1);

	let searchState = $state<'idle' | 'running' | 'done' | 'error'>('idle');
	let searchError = $state<string | null>(null);
	let paretoPoints = $state<ParetoPoint[]>([]);
	let sortKey = $state<string>('manufacturing cost');

	const sortedPoints = $derived(
		[...paretoPoints].sort((a, b) => (a.objective_values[sortKey] ?? 0) - (b.objective_values[sortKey] ?? 0))
	);
	const objectiveNames = $derived(paretoPoints.length > 0 ? Object.keys(paretoPoints[0].objective_values) : []);

	function bestBy(name: string, points: ParetoPoint[]): ParetoPoint | null {
		if (points.length === 0) return null;
		return points.reduce((best, p) =>
			(p.objective_values[name] ?? Infinity) < (best.objective_values[name] ?? Infinity) ? p : best
		);
	}
	function worstBy(name: string, points: ParetoPoint[]): ParetoPoint | null {
		if (points.length === 0) return null;
		return points.reduce((best, p) =>
			(p.objective_values[name] ?? -Infinity) > (best.objective_values[name] ?? -Infinity) ? p : best
		);
	}
	function rangeKey(names: string[]): string | undefined {
		return names.find((n) => n.startsWith('range @'));
	}

	const cheapest = $derived(bestBy('manufacturing cost', paretoPoints));
	const fastest = $derived(bestBy('0-60 mph time', paretoPoints));
	const bestRangePoint = $derived.by(() => {
		const key = rangeKey(objectiveNames);
		return key ? worstBy(key, paretoPoints) : null;
	});
	const bestRangeValue = $derived.by(() => {
		const key = rangeKey(objectiveNames);
		return key && bestRangePoint ? bestRangePoint.objective_values[key] : null;
	});

	// How this platform's own designs actually stack up against the real,
	// currently-shipping EV market on $/mile of range -- the one dimension
	// both sides have real, comparable numbers for (see MSRP_MARKUP_FACTOR).
	const marketComparison = $derived.by(() => {
		const rKey = rangeKey(objectiveNames);
		if (!rKey || paretoPoints.length === 0 || benchmarkVehicles.length === 0) return null;
		const marketCostPerMile = benchmarkVehicles.map((v) => v.msrp_usd / v.epa_range_mi);
		const marketMedian = [...marketCostPerMile].sort((a, b) => a - b)[Math.floor(marketCostPerMile.length / 2)];
		const beatMarket = paretoPoints.filter((p) => {
			const estMsrp = p.objective_values['manufacturing cost'] * MSRP_MARKUP_FACTOR;
			return estMsrp / p.objective_values[rKey] < marketMedian;
		}).length;
		return { beatMarket, total: paretoPoints.length, marketMedian };
	});

	const ARCH_COLORS: Record<string, string> = {
		pm_synchronous: '#4f8cf7',
		switched_reluctance: '#f2994a',
		induction: '#2dd4a7'
	};
	let chartCanvas = $state<HTMLCanvasElement | null>(null);

	$effect(() => {
		const canvas = chartCanvas;
		const points = paretoPoints;
		const rKey = rangeKey(objectiveNames);
		if (!canvas || points.length === 0 || !rKey) return;

		const costKey = 'manufacturing cost';
		const timeKey = '0-60 mph time';
		const byArch: Record<string, { x: number; y: number; r: number }[]> = {};
		for (const p of points) {
			const arch = p.candidate.motor_architecture;
			(byArch[arch] ??= []).push({
				x: p.objective_values[costKey],
				y: p.objective_values[timeKey],
				r: Math.max(4, Math.sqrt(p.objective_values[rKey]) * 0.9)
			});
		}
		const datasets = Object.entries(byArch).map(([arch, data]) => ({
			label: arch,
			data,
			backgroundColor: (ARCH_COLORS[arch] ?? '#9aa4b5') + 'aa',
			borderColor: ARCH_COLORS[arch] ?? '#9aa4b5'
		}));

		const instance = new Chart(canvas, {
			type: 'bubble',
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
								const raw = ctx.raw as { x: number; y: number };
								return `$${raw.x.toLocaleString()}, ${raw.y.toFixed(1)}s`;
							}
						}
					}
				},
				scales: {
					x: {
						title: { display: true, text: 'manufacturing cost ($)', color: '#8b93a3' },
						ticks: { color: '#5b6272' },
						grid: { color: '#1c212a' }
					},
					y: {
						title: { display: true, text: '0-60 mph (s)', color: '#8b93a3' },
						ticks: { color: '#5b6272' },
						grid: { color: '#1c212a' }
					}
				}
			}
		});

		return () => instance.destroy();
	});

	let marketChartCanvas = $state<HTMLCanvasElement | null>(null);

	$effect(() => {
		const canvas = marketChartCanvas;
		const points = paretoPoints;
		const market = benchmarkVehicles;
		const rKey = rangeKey(objectiveNames);
		if (!canvas || points.length === 0 || market.length === 0 || !rKey) return;

		const instance = new Chart(canvas, {
			type: 'scatter',
			data: {
				datasets: [
					{
						label: 'real production EVs',
						data: market.map((v) => ({ x: v.msrp_usd, y: v.epa_range_mi })),
						backgroundColor: 'rgba(139, 147, 163, 0.5)',
						borderColor: '#8b93a3',
						pointRadius: 3
					},
					{
						label: 'your designs',
						data: points.map((p) => ({
							x: p.objective_values['manufacturing cost'] * MSRP_MARKUP_FACTOR,
							y: p.objective_values[rKey]
						})),
						backgroundColor: 'rgba(79, 140, 247, 0.8)',
						borderColor: '#4f8cf7',
						pointRadius: 5
					}
				]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				animation: false,
				plugins: {
					legend: { display: false },
					tooltip: {
						callbacks: {
							label: (ctx) => {
								if (ctx.datasetIndex === 0) {
									const v = market[ctx.dataIndex];
									return `${v.name}: $${v.msrp_usd.toLocaleString()}, ${v.epa_range_mi}mi`;
								}
								const raw = ctx.raw as { x: number; y: number };
								return `your design: ~$${raw.x.toLocaleString(undefined, { maximumFractionDigits: 0 })} est. MSRP, ${raw.y.toFixed(0)}mi`;
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

	onMount(async () => {
		try {
			requirementKinds = await fetchRequirementKinds();
		} catch (e) {
			metadataError = e instanceof Error ? e.message : String(e);
		}
		try {
			benchmarkVehicles = await fetchBenchmarkVehicles();
		} catch {
			// Non-critical: the search itself still works without the market
			// comparison, so a failed fetch here shouldn't block anything --
			// the comparison chart/insight simply won't render.
		}
	});

	function addRequirement() {
		requirements = [...requirements, { kind: requirementKinds[0] ?? 'max_mass_kg', threshold: 0 }];
	}
	function removeRequirement(index: number) {
		requirements = requirements.filter((_, i) => i !== index);
	}

	async function runSearch() {
		searchState = 'running';
		searchError = null;
		paretoPoints = [];
		try {
			const jobId = await startParetoJob(requirements, popSize, nGen, seed);
			while (true) {
				const status = await pollParetoJob(jobId);
				if (status.status === 'done') {
					paretoPoints = status.result.points;
					searchState = 'done';
					if (paretoPoints.length > 0) sortKey = Object.keys(paretoPoints[0].objective_values)[0];
					break;
				}
				if (status.status === 'error') {
					searchError = status.message;
					searchState = 'error';
					break;
				}
				if (status.status === 'not_found') {
					searchError = 'job disappeared from the backend job store';
					searchState = 'error';
					break;
				}
				await new Promise((r) => setTimeout(r, 800));
			}
		} catch (e) {
			searchError = e instanceof Error ? e.message : String(e);
			searchState = 'error';
		}
	}

	// evaluate is its own page; hand it a candidate via sessionStorage so
	// "inspect" from a Pareto point can jump there pre-filled without a
	// server-side session or duplicating the evaluate form on this page.
	function inspect(point: ParetoPoint) {
		sessionStorage.setItem('apex_inspect_candidate', JSON.stringify(point.candidate));
		goto('/evaluate');
	}

	function checkRobustnessFor(point: ParetoPoint) {
		sessionStorage.setItem('apex_inspect_candidate', JSON.stringify(point.candidate));
		goto('/robust');
	}
</script>

<svelte:head>
	<title>Optimizer — APEX</title>
</svelte:head>

<div class="shell">
	<header class="page-header">
		<p class="eyebrow">Generate &amp; optimize</p>
		<h1 class="page-title">Pareto optimizer</h1>
		<p class="page-subtitle">
			Set a mission — the requirements every candidate design must satisfy — then run a real
			NSGA2 search over the design space. No single "best" design, a spread of non-dominated
			trade-offs.
		</p>
	</header>

	{#if metadataError}
		<p class="page-error">Could not load requirement kinds: {metadataError}</p>
	{/if}

	<section class="panel" style="margin-bottom: 1.25rem;">
		<div class="panel-head">
			<span class="panel-index">1</span>
			<div>
				<h2>Mission</h2>
				<p class="hint">
					Defaults match the platform's own worked example: a sub-$42k electric crossover,
					&ge;310mi range, sub-6s 0-60.
				</p>
			</div>
		</div>

		<div class="requirement-list">
			{#each requirements as req, i}
				<div class="requirement-row">
					<select bind:value={req.kind}>
						{#each requirementKinds as kind}
							<option value={kind}>{kind}</option>
						{/each}
					</select>
					<input type="number" bind:value={req.threshold} step="any" />
					<button class="icon-btn" onclick={() => removeRequirement(i)} aria-label="remove requirement"
						>&times;</button
					>
				</div>
			{/each}
		</div>
		<button class="ghost-btn" onclick={addRequirement}>+ add requirement</button>
	</section>

	<section class="panel">
		<div class="panel-head">
			<span class="panel-index">2</span>
			<div>
				<h2>Search</h2>
				<p class="hint">A real NSGA2 Pareto search over battery, motor, gearing, aero, and tires.</p>
			</div>
		</div>

		<div class="search-controls">
			<label>pop size <input type="number" bind:value={popSize} min="4" max="400" /></label>
			<label>generations <input type="number" bind:value={nGen} min="1" max="200" /></label>
			<label>seed <input type="number" bind:value={seed} /></label>
			<button class="primary-btn" onclick={runSearch} disabled={searchState === 'running'}>
				{searchState === 'running' ? 'searching…' : 'run search'}
			</button>
		</div>

		{#if searchState === 'error'}
			<p class="page-error">Search failed: {searchError}</p>
		{/if}

		{#if searchState === 'done'}
			{#if paretoPoints.length === 0}
				<div class="empty-state">
					<p>No non-dominated feasible designs for this mission.</p>
					<p class="hint">
						Try loosening a threshold &mdash; the design space may not contain anything that
						satisfies every requirement at once.
					</p>
				</div>
			{:else}
				<div class="kpi-row">
					<div class="kpi-card">
						<p class="kpi-label">feasible designs</p>
						<p class="kpi-value">{paretoPoints.length}</p>
					</div>
					{#if cheapest}
						<div class="kpi-card">
							<p class="kpi-label">cheapest</p>
							<p class="kpi-value">
								${cheapest.objective_values['manufacturing cost'].toLocaleString(undefined, {
									maximumFractionDigits: 0
								})}
							</p>
						</div>
					{/if}
					{#if fastest}
						<div class="kpi-card">
							<p class="kpi-label">fastest 0-60</p>
							<p class="kpi-value">{fastest.objective_values['0-60 mph time'].toFixed(1)}s</p>
						</div>
					{/if}
					{#if bestRangeValue !== null}
						<div class="kpi-card">
							<p class="kpi-label">best range</p>
							<p class="kpi-value">{bestRangeValue.toFixed(0)}mi</p>
						</div>
					{/if}
				</div>

				<div class="chart-card">
					<p class="chart-caption">cost vs 0-60 &mdash; bubble size is range, color is architecture</p>
					<div class="chart-wrap">
						<!-- svelte-ignore a11y_no_interactive_element_to_noninteractive_role -->
						<canvas
							bind:this={chartCanvas}
							role="img"
							aria-label="Scatter chart of manufacturing cost against 0-60mph time for the non-dominated designs, bubble size shows range"
						></canvas>
					</div>
					<div class="chart-legend">
						{#each Object.entries(ARCH_COLORS) as [arch, color]}
							<span class="legend-item"><span class="legend-swatch" style="background:{color}"
								></span>{arch}</span
							>
						{/each}
					</div>
				</div>

				<div class="results-head">
					<p class="hint">sort by</p>
					<select bind:value={sortKey}>
						{#each objectiveNames as name}
							<option value={name}>{name}</option>
						{/each}
					</select>
				</div>
				<div class="table-wrap">
					<table class="results">
						<thead>
							<tr>
								<th>battery</th><th>motor</th><th>architecture</th><th>chemistry</th><th>tire</th
								><th>#m</th>
								{#each objectiveNames as name}
									<th>{name}</th>
								{/each}
								<th></th>
							</tr>
						</thead>
						<tbody>
							{#each sortedPoints as point}
								<tr>
									<td>{point.candidate.battery_capacity_kwh.toFixed(0)}kWh</td>
									<td>{point.candidate.motor_power_kw.toFixed(0)}kW</td>
									<td>{point.candidate.motor_architecture}</td>
									<td>{point.candidate.battery_chemistry}</td>
									<td>{point.candidate.tire_choice}</td>
									<td>{point.candidate.num_motors}</td>
									{#each objectiveNames as name}
										<td>{point.objective_values[name].toFixed(1)}</td>
									{/each}
									<td>
										<button class="link-btn" onclick={() => inspect(point)}>inspect</button>
										<button class="link-btn" onclick={() => checkRobustnessFor(point)}>robust check</button>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		{/if}
	</section>

	{#if searchState === 'done' && paretoPoints.length > 0 && benchmarkVehicles.length > 0}
		<section class="panel">
			<div class="panel-head">
				<span class="panel-index">3</span>
				<div>
					<h2>Against the real market</h2>
					<p class="hint">
						Your designs plotted against {benchmarkVehicles.length} real, currently-shipping production
						EVs on price vs. range &mdash; the one dimension both sides have comparable numbers for.
						Your cost is manufacturing cost &times; {MSRP_MARKUP_FACTOR} (an estimated MSRP, not a
						real quoted price); see <a href="/methodology">methodology</a> for why range figures aren't
						a perfect match either.
					</p>
				</div>
			</div>

			{#if marketComparison}
				<div class="kpi-row">
					<div class="kpi-card">
						<p class="kpi-label">beat the market median $/mile</p>
						<p class="kpi-value">{marketComparison.beatMarket} / {marketComparison.total}</p>
					</div>
					<div class="kpi-card">
						<p class="kpi-label">market median $/mile of range</p>
						<p class="kpi-value">${marketComparison.marketMedian.toFixed(0)}</p>
					</div>
				</div>
			{/if}

			<div class="chart-card">
				<div class="chart-wrap">
					<!-- svelte-ignore a11y_no_interactive_element_to_noninteractive_role -->
					<canvas
						bind:this={marketChartCanvas}
						role="img"
						aria-label="Scatter chart comparing your generated designs against real production EVs on estimated MSRP vs range"
					></canvas>
				</div>
				<div class="chart-legend">
					<span class="legend-item"><span class="legend-swatch" style="background:#8b93a3"></span
						>real production EVs</span
					>
					<span class="legend-item"><span class="legend-swatch" style="background:#4f8cf7"></span
						>your designs</span
					>
				</div>
			</div>
		</section>
	{/if}
</div>

<style>
	.requirement-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-bottom: 0.85rem;
	}
	.requirement-row {
		display: grid;
		grid-template-columns: 1fr 140px 32px;
		gap: 0.6rem;
		align-items: center;
	}
	.search-controls {
		display: flex;
		gap: 1.25rem;
		align-items: end;
		flex-wrap: wrap;
		margin-bottom: 1rem;
	}
	.search-controls label {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
		font-size: 0.8rem;
		color: var(--text-dim);
	}
	.search-controls input {
		width: 90px;
	}
	.chart-card {
		background: var(--field);
		border: 1px solid rgba(255, 255, 255, 0.06);
		border-radius: 10px;
		padding: 1rem 1.1rem;
		margin-bottom: 1.25rem;
	}
	.chart-caption {
		font-size: 0.78rem;
		color: var(--text-dim);
		margin: 0 0 0.75rem;
	}
	.chart-wrap {
		position: relative;
		width: 100%;
		height: 300px;
	}
	.chart-legend {
		display: flex;
		gap: 1.25rem;
		flex-wrap: wrap;
		margin-top: 0.6rem;
		font-size: 0.78rem;
		color: var(--text-dim);
	}
	.legend-item {
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}
	.legend-swatch {
		width: 9px;
		height: 9px;
		border-radius: 2px;
		display: inline-block;
	}
	.results-head {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		margin-bottom: 0.6rem;
	}
	.results-head .hint {
		margin: 0;
	}
</style>
