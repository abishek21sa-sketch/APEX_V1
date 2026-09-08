<script lang="ts">
	import { onMount } from 'svelte';
	import {
		checkRobustness,
		fetchDesignSpace,
		fetchRobustRequirementKinds,
		type CandidateSpec,
		type DesignSpace,
		type RequirementSpec,
		type RobustCheckResponse
	} from '$lib/api';

	let designSpace = $state<DesignSpace | null>(null);
	let requirementKinds = $state<string[]>([]);
	let metadataError = $state<string | null>(null);
	let loadedFromInspect = $state(false);

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

	let requirements = $state<RequirementSpec[]>([
		{ kind: 'max_acceleration_time_s', threshold: 6.0 },
		{ kind: 'min_highway_range_mi', threshold: 310.0 }
	]);
	let nSamples = $state(200);
	let seed = $state(1);

	let result = $state<RobustCheckResponse | null>(null);
	let checkError = $state<string | null>(null);
	let checkLoading = $state(false);

	onMount(async () => {
		try {
			[designSpace, requirementKinds] = await Promise.all([fetchDesignSpace(), fetchRobustRequirementKinds()]);
		} catch (e) {
			metadataError = e instanceof Error ? e.message : String(e);
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

	function addRequirement() {
		requirements = [...requirements, { kind: requirementKinds[0] ?? 'max_acceleration_time_s', threshold: 0 }];
	}
	function removeRequirement(index: number) {
		requirements = requirements.filter((_, i) => i !== index);
	}

	async function runCheck() {
		checkLoading = true;
		checkError = null;
		result = null;
		try {
			result = await checkRobustness(candidate, requirements, nSamples, seed);
		} catch (e) {
			checkError = e instanceof Error ? e.message : String(e);
		} finally {
			checkLoading = false;
		}
	}
</script>

<svelte:head>
	<title>Robust check — APEX</title>
</svelte:head>

<div class="shell">
	<header class="page-header">
		<p class="eyebrow">Monte Carlo robust design</p>
		<h1 class="page-title">Robust check</h1>
		<p class="page-subtitle">
			A design that passes at nominal conditions (Evaluate's single operating point) can still
			fail once payload, ambient temperature, road grade, tire wear, and battery aging are allowed
			to vary. This runs {nSamples} sampled scenarios and reports the fraction each requirement
			actually holds under &mdash; a chance-constrained check, not a pass/fail on one number.
		</p>
	</header>

	{#if metadataError}
		<p class="page-error">Could not load metadata: {metadataError}</p>
	{/if}

	<section class="panel" style="margin-bottom: 1.25rem;">
		<div class="panel-head">
			<span class="panel-index">1</span>
			<div>
				<h2>Candidate</h2>
				{#if loadedFromInspect}
					<p class="hint">Loaded from a Pareto search result or a saved design you opened.</p>
				{/if}
			</div>
		</div>
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
		{:else}
			<p class="hint">Loading design-space metadata&hellip;</p>
		{/if}
	</section>

	<section class="panel">
		<div class="panel-head">
			<span class="panel-index">2</span>
			<div>
				<h2>Requirements &amp; sampling</h2>
				<p class="hint">
					Only requirement kinds the robust checker supports are offered here &mdash; manufacturing
					cost isn't, since it doesn't vary with the operating scenario (see
					<a href="/methodology">methodology</a>).
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

		<div class="search-controls" style="margin-top: 1.25rem;">
			<label>samples <input type="number" bind:value={nSamples} min="10" max="2000" /></label>
			<label>seed <input type="number" bind:value={seed} /></label>
			<button class="primary-btn" onclick={runCheck} disabled={checkLoading || requirements.length === 0}>
				{checkLoading ? 'sampling…' : 'check robustness'}
			</button>
		</div>

		{#if checkError}
			<p class="page-error" style="margin-top: 1rem;">{checkError}</p>
		{/if}

		{#if result}
			<div class="kpi-row" style="margin-top: 1.5rem;">
				<div class="kpi-card">
					<p class="kpi-label">robustly feasible</p>
					<p class="kpi-value" style="color: {result.robustly_feasible ? 'var(--success)' : 'var(--danger)'}">
						{result.robustly_feasible ? 'yes' : 'no'}
					</p>
				</div>
				<div class="kpi-card">
					<p class="kpi-label">scenarios sampled</p>
					<p class="kpi-value">{result.n_samples}</p>
				</div>
			</div>

			<div class="table-wrap">
				<table class="results">
					<thead>
						<tr>
							<th>requirement</th><th>threshold</th><th>reliability target</th><th
								>fraction satisfied</th
							><th>nominal value</th><th>worst sampled</th><th>verdict</th>
						</tr>
					</thead>
					<tbody>
						{#each result.requirements as r}
							<tr>
								<td>{r.name}</td>
								<td>{r.threshold}{r.unit}</td>
								<td>{(r.reliability_target * 100).toFixed(0)}%</td>
								<td>{(r.fraction_satisfied * 100).toFixed(1)}%</td>
								<td>{r.nominal_value.toFixed(2)}{r.unit}</td>
								<td>{r.worst_value.toFixed(2)}{r.unit}</td>
								<td style="color: {r.satisfied ? 'var(--success)' : 'var(--danger)'}">
									{r.satisfied ? 'pass' : 'fail'}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</section>
</div>

<style>
	.candidate-form {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
		gap: 0.85rem;
		max-width: 62em;
	}
	.candidate-form label {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
		font-size: 0.8rem;
		color: var(--text-dim);
	}
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
</style>
