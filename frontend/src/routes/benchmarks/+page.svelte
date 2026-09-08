<script lang="ts">
	import { onMount } from 'svelte';
	import Chart from 'chart.js/auto';
	import { fetchBenchmarkVehicles, type BenchmarkVehicle } from '$lib/api';

	let vehicles = $state<BenchmarkVehicle[]>([]);
	let loadError = $state<string | null>(null);
	let loading = $state(true);

	let search = $state('');
	let typeFilter = $state('all');
	let sortKey = $state<'name' | 'msrp_usd' | 'epa_range_mi' | 'cost_per_mile'>('msrp_usd');

	const vehicleTypes = $derived(['all', ...new Set(vehicles.map((v) => v.vehicle_type))].sort());

	function costPerMile(v: BenchmarkVehicle): number {
		return v.msrp_usd / v.epa_range_mi;
	}

	const filtered = $derived(
		vehicles
			.filter((v) => typeFilter === 'all' || v.vehicle_type === typeFilter)
			.filter((v) => v.name.toLowerCase().includes(search.toLowerCase()))
	);
	const sorted = $derived(
		[...filtered].sort((a, b) => {
			if (sortKey === 'name') return a.name.localeCompare(b.name);
			if (sortKey === 'cost_per_mile') return costPerMile(a) - costPerMile(b);
			return a[sortKey] - b[sortKey];
		})
	);

	let chartCanvas = $state<HTMLCanvasElement | null>(null);

	$effect(() => {
		const canvas = chartCanvas;
		const points = vehicles;
		if (!canvas || points.length === 0) return;

		const instance = new Chart(canvas, {
			type: 'scatter',
			data: {
				datasets: [
					{
						label: 'production EVs',
						data: points.map((v) => ({ x: v.msrp_usd, y: v.epa_range_mi })),
						backgroundColor: 'rgba(34, 211, 238, 0.55)',
						borderColor: '#22d3ee'
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
								const v = points[ctx.dataIndex];
								return `${v.name}: $${v.msrp_usd.toLocaleString()}, ${v.epa_range_mi}mi`;
							}
						}
					}
				},
				scales: {
					x: {
						title: { display: true, text: 'MSRP ($)', color: '#8b93a3' },
						ticks: { color: '#5b6272' },
						grid: { color: '#1c212a' }
					},
					y: {
						title: { display: true, text: 'EPA range (mi)', color: '#8b93a3' },
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
			vehicles = await fetchBenchmarkVehicles();
		} catch (e) {
			loadError = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	});
</script>

<svelte:head>
	<title>Benchmarks — APEX</title>
</svelte:head>

<div class="shell">
	<header class="page-header">
		<p class="eyebrow">The real 2026 EV market</p>
		<h1 class="page-title">Benchmarks</h1>
		<p class="page-subtitle">
			{vehicles.length || '98'} currently-shipping production EVs across every segment, with real
			published price and EPA range — not simulated. Sourced from a public 2026-model-year US EV
			comparison table.
		</p>
	</header>

	{#if loadError}
		<p class="page-error">Could not load benchmark vehicles: {loadError}</p>
	{:else if loading}
		<p class="hint">Loading&hellip;</p>
	{:else}
		<section class="panel" style="margin-bottom: 1.25rem;">
			<p class="chart-caption">price vs EPA range, all {vehicles.length} vehicles</p>
			<div class="chart-wrap">
				<!-- svelte-ignore a11y_no_interactive_element_to_noninteractive_role -->
				<canvas
					bind:this={chartCanvas}
					role="img"
					aria-label="Scatter chart of MSRP against EPA range for {vehicles.length} production electric vehicles"
				></canvas>
			</div>
		</section>

		<section class="panel">
			<div class="filter-row">
				<input type="text" placeholder="search by model&hellip;" bind:value={search} />
				<select bind:value={typeFilter}>
					{#each vehicleTypes as t}
						<option value={t}>{t === 'all' ? 'all types' : t}</option>
					{/each}
				</select>
				<select bind:value={sortKey}>
					<option value="msrp_usd">sort: price</option>
					<option value="epa_range_mi">sort: range</option>
					<option value="cost_per_mile">sort: $/mile of range</option>
					<option value="name">sort: name</option>
				</select>
				<p class="hint" style="margin-left: auto;">{sorted.length} of {vehicles.length}</p>
			</div>

			<div class="table-wrap">
				<table class="results">
					<thead>
						<tr>
							<th>model</th><th>type</th><th>drivetrain</th><th>MSRP</th><th>EPA range</th><th
								>$/mile of range</th
							>
						</tr>
					</thead>
					<tbody>
						{#each sorted as v}
							<tr>
								<td>{v.name}</td>
								<td>{v.vehicle_type}</td>
								<td>{v.drivetrain}</td>
								<td>${v.msrp_usd.toLocaleString()}</td>
								<td>{v.epa_range_mi.toFixed(0)}mi</td>
								<td>${costPerMile(v).toFixed(0)}</td>
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
	.filter-row {
		display: flex;
		gap: 0.75rem;
		align-items: center;
		flex-wrap: wrap;
		margin-bottom: 1rem;
	}
	.filter-row input {
		min-width: 200px;
	}
</style>
