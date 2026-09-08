<svelte:head>
	<title>Methodology — APEX</title>
</svelte:head>

<div class="shell">
	<header class="page-header">
		<p class="eyebrow">How this actually works</p>
		<h1 class="page-title">Methodology</h1>
		<p class="page-subtitle">
			What each piece of APEX actually computes, and where the real limitations are &mdash; written
			plainly rather than glossed over.
		</p>
	</header>

	<section class="doc-section">
		<h2>1. Physics kernel</h2>
		<p>
			Every candidate design is scored by simulating it, not by a learned score. Longitudinal
			dynamics come from the road-load equation (aerodynamic drag, rolling resistance, grade) and
			tractive-force limits (torque-limited, power-limited, and RPM-redline-limited regions of the
			motor's operating envelope). The battery is modeled as an equivalent circuit &mdash; open-circuit
			voltage, internal resistance, asymmetric thermal derating between charge and discharge &mdash;
			and the motor has a real speed/torque-aware efficiency map, not a flat efficiency constant.
		</p>
		<p class="doc-note">
			Known simplification: traction is assumed available to the full vehicle mass (effectively
			AWD) &mdash; a front/rear weight-transfer model belongs to a lateral vehicle-dynamics layer this
			kernel doesn't implement. There's also no electronic top-speed governor; the kernel reports
			the physics ceiling, which is why a governed production car's real top speed can sit below
			what this model would predict for the same specs.
		</p>
	</section>

	<section class="doc-section">
		<h2>2. Design space &amp; buildup</h2>
		<p>
			The design space mixes continuous variables (battery capacity, motor power, gear ratio, drag
			coefficient, frontal area) with discrete choices (motor architecture, battery chemistry, tire
			compound, single vs. dual motor). A buildup step turns any point in that space into mass and
			manufacturing cost, which is what candidates actually get optimized against alongside
			performance and range.
		</p>
	</section>

	<section class="doc-section">
		<h2>3. Multi-objective optimization</h2>
		<p>
			Search runs NSGA2 (a real genetic multi-objective algorithm, via pymoo) over the mixed
			design space, producing a Pareto frontier &mdash; the set of designs where improving one
			objective (cost, mass, 0-60 time, range) necessarily makes another one worse. There is
			deliberately no single "best" design or invented composite score collapsing the trade-offs
			into one number.
		</p>
	</section>

	<section class="doc-section">
		<h2>4. Robust design under uncertainty</h2>
		<p>
			A design that's optimal on paper can still fail in practice. The robust checker runs Monte
			Carlo sampling across realistic operating scenarios &mdash; payload, ambient temperature, road
			grade, tire wear, battery aging &mdash; and reports a chance-constrained feasibility rate: what
			fraction of sampled conditions the design actually holds up under, not just its nominal
			performance.
		</p>
	</section>

	<section class="doc-section">
		<h2>5. Surrogate models &amp; active learning</h2>
		<p>
			Separately from the live optimizer, the platform includes Gaussian Process and Random Forest
			surrogate models trained on a Latin-Hypercube-sampled simulation dataset, and a pool-based
			active-learning loop comparing uncertainty sampling against random sampling. This is a
			research capability for studying how well a learned model can approximate the real physics
			kernel and how efficiently it can be trained &mdash; it is not used to score candidates in the
			optimizer or the agent; every actual evaluation still runs the real physics.
		</p>
	</section>

	<section class="doc-section">
		<h2>6. The engineer agent</h2>
		<p>
			The agent chat is Claude Opus 5 running a tool-calling loop restricted to seven of this
			platform's own functions &mdash; get the design space, evaluate a candidate, run a Pareto
			search, check a robust-feasibility constraint, and a few more. It cannot invent numbers
			outside what those tools return. Each request is single-turn: the agent has no memory of
			earlier messages in the same session, since there's no server-side conversation store yet.
		</p>
	</section>

	<section class="doc-section">
		<h2>7. Three-tier architecture</h2>
		<p>
			A Python FastAPI service runs the physics, the optimizer, and the agent's tools &mdash;
			synchronous and blocking by design, since its whole job is "compute and return." A Rust/Axum
			backend handles orchestration: routing, and running the slow Pareto search as a background
			job the frontend polls, so the browser never blocks on a multi-second search. The SvelteKit
			frontend is the actual workstation UI, talking to the Rust backend, which proxies to Python.
		</p>
	</section>
</div>

<style>
	.doc-section {
		max-width: 62em;
		margin-bottom: 2.4rem;
	}
	.doc-section h2 {
		font-size: 1.05rem;
		font-weight: 600;
		margin: 0 0 0.7rem;
		padding-bottom: 0.5rem;
		border-bottom: 1px solid var(--seam);
	}
	.doc-section p {
		font-size: 0.9rem;
		line-height: 1.75;
		color: var(--text-dim);
		margin: 0 0 0.9rem;
	}
	.doc-note {
		background: var(--amber-soft);
		border-left: 2px solid var(--amber);
		border-radius: 0 8px 8px 0;
		padding: 0.75rem 1rem;
		font-size: 0.85rem !important;
		color: var(--text) !important;
	}
</style>
