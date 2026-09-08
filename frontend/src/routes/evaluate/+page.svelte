<script lang="ts">
	import { onMount } from 'svelte';
	import {
		evaluateCandidate,
		fetchBenchmarkVehicles,
		fetchDesignSpace,
		type BenchmarkVehicle,
		type CandidateSpec,
		type DesignSpace,
		type EvaluateResponse
	} from '$lib/api';
	import { saveDesign } from '$lib/savedDesigns';

	// Same manufacturing-cost -> MSRP markup used on /optimizer and elsewhere
	// in this codebase (see apex.design.constraints.example_crossover_mission).
	const MSRP_MARKUP_FACTOR = 1.4;

	let designSpace = $state<DesignSpace | null>(null);
	let metadataError = $state<string | null>(null);
	let loadedFromInspect = $state(false);
	let benchmarkVehicles = $state<BenchmarkVehicle[]>([]);

	let candidate = $state<CandidateSpec>({
		battery_capacity_kwh: 78,
		motor_power_kw: 220,
		gear_ratio: 8.5,
		drag_coefficient: 0.24,
		frontal_area_m2: 2.25,
		motor_architecture: 'pm_synchronous',
		battery_chemistry: 'lfp',
		num_motors: '1',
		tire_choice: 'eco_low_rolling_resistance'
	});
	let evalResult = $state<EvaluateResponse | null>(null);
	let evalError = $state<string | null>(null);
	let evalLoading = $state(false);

	onMount(async () => {
		try {
			designSpace = await fetchDesignSpace();
		} catch (e) {
			metadataError = e instanceof Error ? e.message : String(e);
		}
		try {
			benchmarkVehicles = await fetchBenchmarkVehicles();
		} catch {
			// Non-critical -- evaluate itself still works without market position.
		}

		const stored = sessionStorage.getItem('apex_inspect_candidate');
		if (stored) {
			try {
				candidate = JSON.parse(stored) as CandidateSpec;
				loadedFromInspect = true;
			} catch {
				// malformed sessionStorage payload -- ignore, keep the default candidate
			}
			sessionStorage.removeItem('apex_inspect_candidate');
		}
	});

	async function runEvaluate() {
		evalLoading = true;
		evalError = null;
		evalResult = null;
		try {
			evalResult = await evaluateCandidate(candidate);
		} catch (e) {
			evalError = e instanceof Error ? e.message : String(e);
		} finally {
			evalLoading = false;
		}
	}

	const estimatedMsrp = $derived(evalResult ? evalResult.manufacturing_cost_usd * MSRP_MARKUP_FACTOR : null);

	// The closest real vehicles by price -- what an engineer would actually
	// cross-shop this design against, not just an abstract market median.
	const nearestByPrice = $derived.by(() => {
		if (!estimatedMsrp || benchmarkVehicles.length === 0) return [];
		return [...benchmarkVehicles]
			.sort((a, b) => Math.abs(a.msrp_usd - estimatedMsrp) - Math.abs(b.msrp_usd - estimatedMsrp))
			.slice(0, 5);
	});
	const marketMedianCostPerMile = $derived.by(() => {
		if (benchmarkVehicles.length === 0) return null;
		const values = benchmarkVehicles.map((v) => v.msrp_usd / v.epa_range_mi).sort((a, b) => a - b);
		return values[Math.floor(values.length / 2)];
	});
	const thisCostPerMile = $derived(
		evalResult && estimatedMsrp ? estimatedMsrp / evalResult.range_mi : null
	);

	function printSpecSheet() {
		window.print();
	}

	let saveConfirmation = $state<string | null>(null);

	function handleSaveDesign() {
		if (!evalResult) return;
		saveDesign(candidate, evalResult);
		saveConfirmation = 'Saved. View it on the Saved page.';
		setTimeout(() => (saveConfirmation = null), 3000);
	}
</script>

<svelte:head>
	<title>Evaluate — APEX</title>
</svelte:head>

<div class="shell">
	<header class="page-header">
		<p class="eyebrow">Single candidate</p>
		<h1 class="page-title">Evaluate</h1>
		<p class="page-subtitle">
			Run the full physics kernel on one specific design, independent of any mission or search.
		</p>
	</header>

	{#if metadataError}
		<p class="page-error">Could not load design-space metadata: {metadataError}</p>
	{/if}

	<section class="panel">
		{#if loadedFromInspect}
			<p class="hint no-print" style="margin-bottom: 1rem;">
			Loaded from a Pareto search result or a saved design you opened.
		</p>
		{/if}
		{#if designSpace}
			<div class="candidate-form">
				{#each designSpace.continuous as v}
					<label>
						{v.name} ({v.unit})
						<input
							type="number"
							min={v.lower}
							max={v.upper}
							step="any"
							bind:value={candidate[v.name as keyof CandidateSpec] as number}
						/>
					</label>
				{/each}
				{#each designSpace.discrete as v}
					<label>
						{v.name}
						<select bind:value={candidate[v.name as keyof CandidateSpec] as string}>
							{#each v.choices as choice}
								<option value={choice}>{choice}</option>
							{/each}
						</select>
					</label>
				{/each}
			</div>
			<button class="primary-btn no-print" onclick={runEvaluate} disabled={evalLoading}
				>{evalLoading ? 'evaluating…' : 'evaluate'}</button
			>

			{#if evalError}
				<p class="page-error" style="margin-top: 1rem;">{evalError}</p>
			{/if}
			{#if evalResult}
				<div class="spec-sheet">
					<div class="spec-sheet-head">
						<div>
							<p class="eyebrow" style="margin-bottom: 0.25rem;">Spec sheet</p>
							<h2 style="margin:0;font-size:1.05rem;">{evalResult.vehicle_name}</h2>
						</div>
						<div class="no-print spec-sheet-actions">
							{#if saveConfirmation}
								<span class="hint">{saveConfirmation}</span>
							{/if}
							<button class="ghost-btn" onclick={handleSaveDesign}>save design</button>
							<button class="ghost-btn" onclick={printSpecSheet}>print / save as PDF</button>
						</div>
					</div>

					<div class="kpi-row" style="margin-top: 1.25rem;">
						<div class="kpi-card">
							<p class="kpi-label">mass</p>
							<p class="kpi-value">{evalResult.mass_kg.toFixed(0)}kg</p>
						</div>
						<div class="kpi-card">
							<p class="kpi-label">manufacturing cost</p>
							<p class="kpi-value">
								${evalResult.manufacturing_cost_usd.toLocaleString(undefined, { maximumFractionDigits: 0 })}
							</p>
						</div>
						<div class="kpi-card">
							<p class="kpi-label">0-60 mph</p>
							<p class="kpi-value">{evalResult.zero_to_sixty_s.toFixed(1)}s</p>
						</div>
						<div class="kpi-card">
							<p class="kpi-label">range @ 65mph</p>
							<p class="kpi-value">{evalResult.range_mi.toFixed(0)}mi</p>
						</div>
					</div>

					<div class="breakdown-grid">
						<div>
							<p class="breakdown-title">Cost breakdown</p>
							<table class="breakdown-table">
								<tbody>
									<tr><td>Glider (body, interior, brakes)</td><td>${evalResult.cost_breakdown.glider_usd.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td></tr>
									<tr><td>Battery</td><td>${evalResult.cost_breakdown.battery_usd.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td></tr>
									<tr><td>Motor(s)</td><td>${evalResult.cost_breakdown.motor_usd.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td></tr>
									<tr><td>Tire delta</td><td>${evalResult.cost_breakdown.tire_delta_usd.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td></tr>
									<tr class="breakdown-total"><td>Total manufacturing cost</td><td>${evalResult.cost_breakdown.total_usd.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td></tr>
									<tr class="breakdown-note"><td colspan="2">Estimated MSRP (&times;{MSRP_MARKUP_FACTOR}): ${estimatedMsrp?.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td></tr>
								</tbody>
							</table>
						</div>
						<div>
							<p class="breakdown-title">Mass breakdown</p>
							<table class="breakdown-table">
								<tbody>
									<tr><td>Glider</td><td>{evalResult.mass_breakdown.glider_kg.toFixed(0)}kg</td></tr>
									<tr><td>Battery</td><td>{evalResult.mass_breakdown.battery_kg.toFixed(0)}kg</td></tr>
									<tr><td>Motor(s)</td><td>{evalResult.mass_breakdown.motor_kg.toFixed(0)}kg</td></tr>
									<tr><td>Tire delta</td><td>{evalResult.mass_breakdown.tire_delta_kg.toFixed(0)}kg</td></tr>
									<tr class="breakdown-total"><td>Total mass</td><td>{evalResult.mass_breakdown.total_kg.toFixed(0)}kg</td></tr>
								</tbody>
							</table>
						</div>
					</div>

					{#if nearestByPrice.length > 0}
						<p class="breakdown-title" style="margin-top: 1.5rem;">Against the real market</p>
						<p class="hint" style="margin-bottom: 0.75rem;">
							Nearest real production EVs by price, and how this design's $/mile of range compares to
							the market median (${marketMedianCostPerMile?.toFixed(0)}/mi).
							{#if thisCostPerMile !== null && marketMedianCostPerMile !== null}
								This design: ${thisCostPerMile.toFixed(0)}/mi
								({thisCostPerMile < marketMedianCostPerMile ? 'better than' : 'worse than'} median).
							{/if}
						</p>
						<div class="table-wrap">
							<table class="results">
								<thead>
									<tr><th>model</th><th>type</th><th>MSRP</th><th>EPA range</th></tr>
								</thead>
								<tbody>
									{#each nearestByPrice as v}
										<tr>
											<td>{v.name}</td>
											<td>{v.vehicle_type}</td>
											<td>${v.msrp_usd.toLocaleString()}</td>
											<td>{v.epa_range_mi.toFixed(0)}mi</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{/if}
				</div>
			{/if}
		{:else}
			<p class="hint">Loading design-space metadata&hellip;</p>
		{/if}
	</section>
</div>

<style>
	.candidate-form {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
		gap: 0.85rem;
		max-width: 62em;
		margin-bottom: 1rem;
	}
	.candidate-form label {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
		font-size: 0.8rem;
		color: var(--text-dim);
	}

	.spec-sheet {
		margin-top: 1.5rem;
		padding-top: 1.25rem;
		border-top: 1px solid var(--seam);
	}
	.spec-sheet-head {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		flex-wrap: wrap;
		gap: 0.75rem;
	}
	.spec-sheet-actions {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.breakdown-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
		gap: 1.5rem;
		margin-top: 1.5rem;
	}
	.breakdown-title {
		font-size: 0.85rem;
		font-weight: 600;
		margin: 0 0 0.6rem;
	}
	.breakdown-table {
		width: 100%;
		font-size: 0.85rem;
	}
	.breakdown-table td {
		padding: 0.35rem 0;
		border-bottom: 1px solid var(--seam);
	}
	.breakdown-table td:last-child {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.breakdown-total td {
		font-weight: 700;
		border-bottom: none;
		border-top: 1px solid var(--seam-strong);
		padding-top: 0.5rem;
	}
	.breakdown-note td {
		border-bottom: none;
		color: var(--text-dim);
		font-size: 0.78rem;
		padding-top: 0.4rem;
	}

	@media print {
		:global(header.topbar),
		:global(.page-header .eyebrow),
		:global(.candidate-form),
		:global(.no-print) {
			display: none !important;
		}
		:global(body) {
			background: white;
			color: black;
		}
		:global(.panel) {
			border: none;
			padding: 0;
		}
		.spec-sheet {
			border-top: none;
		}
		:global(.kpi-card),
		:global(.results tbody tr:hover) {
			background: none;
		}
	}
</style>
