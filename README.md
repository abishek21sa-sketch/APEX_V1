## AIRLINES-1.5× DEPTH CANDIDATE

Current release `APEX_V1_FORTUNE50_AIRLINES15X_RC4` adds a live empirical/historical analysis layer, 26+ substantive workspaces, project-native domain diagnostics, external-source refresh/provenance, and AI decisions grounded in explicit evidence mode. See `docs/AIRLINES_15X_RELEASE.md`.

# Fortune-50 TENX analytical release

**Internal portfolio target:** Math 10/10 · UI 10/10 · AI 10/10, subject to the evidence boundaries below.

- Repository-authored algorithm: **ARCH-SHIELD-v1**
- Unique predictive-learning family: **Bootstrap neural-network surrogate ensemble**
- Analytical AI role: **AI Vehicle Design Council**
- TENX workspaces: **21**
- Operational authority: **human-gated; autonomous execution blocked**

### Test the TENX layer on Windows

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows_tenx_acceptance.ps1
.\scripts\start_tenx_workstation.ps1
```

The first command validates prediction → decision → counterfactual → OR escalation → user-aid behavior and a five-seed originality stress suite. The second opens the dedicated analytical workstation.

> **Evidence boundary:** TENX bundled metrics are synthetic/reference validation, not field deployment validation. Existing native Windows, Julia/Go/Rust/frontend, external-data, clinical, or production gates remain applicable where documented.

---


## Portfolio RC1 — APEX-RDS robust architecture selection

APEX now adds APEX-RDS on top of nominal Pareto search. A shortlisted architecture set is re-evaluated under common uncertainty scenarios and ranked lexicographically by robust feasibility, reliability-target shortfall, upper-tail CVaR of normalized requirement violation, mean violation, and only then manufacturing cost. This prevents a cheaper nominal design from outranking an architecture that actually satisfies the governed reliability envelope.

# APEX — Vehicle Architecture & Engineering Optimization Platform

AI + operations-research platform for vehicle-level engineering design optimization:
given performance, range, packaging, cost, and regulatory requirements, recommend
Pareto-optimal vehicle architectures (battery, motor, gearing, aero, mass, suspension,
thermal) rather than optimizing how a fixed design gets manufactured.

## Status: Phase 10 — benchmark validation, stress testing, acceptance

This repository implements all ten phases of the roadmap: a first-principles
longitudinal-vehicle-dynamics kernel, a battery equivalent-circuit model and a
speed/torque-aware motor efficiency map, a mixed continuous/discrete design space
with a mass/cost buildup and engineering-requirement constraint system, a real
NSGA2 Pareto search over that space, Monte Carlo uncertainty propagation with a
chance-constrained robust-feasibility check, Gaussian Process / Random Forest
surrogate models trained on a real Latin-Hypercube-sampled simulation dataset, a
pool-based active-learning loop, a three-tier web platform (Python scientific
service, Rust orchestration backend, SvelteKit engineering workstation), an LLM
tool-calling agent restricted to seven tools over that same kernel, and — this
phase — a consolidated benchmark harness, stress tests (design-space boundary
corners, cumulative memory pressure across a heavy operation sequence, Rust
job-store concurrency safety), a from-scratch clean-environment verification of
every setup instruction in this README, and containerization for all three
services — since verified live, including a real Docker build that caught and
fixed a genuine bug (see the Phase 10 section below). The engineer agent also
now has a UI panel wired in and has been run live against a real
ANTHROPIC_API_KEY through the full Docker stack, including a hard multi-hop
query that hit `max_hops` and still produced a complete, correctly-reasoned
answer — see "What's actually verified, and what isn't" under Phase 9 below
for what that request actually did.

### Architecture at a glance

```
src/apex/            the computational core (Phases 1-7), pure Python, no I/O
├── physics/           Phase 1-2: vehicle dynamics, battery, motor
├── design/            Phase 3: design space, mass/cost buildup, constraints
├── optimize/          Phase 4: NSGA2 Pareto search
├── robust/            Phase 5: Monte Carlo robust-design checking
├── surrogate/         Phase 6: GP/RF surrogate models
└── active_learning/   Phase 7: uncertainty-driven sampling

service/    Phase 8: FastAPI wrapper around apex/, plus Phase 9's /agent/chat
agent/      Phase 9: the Vehicle Systems Engineer Agent's tools + loop
backend/    Phase 8: Rust/Axum orchestration (async job queue for slow requests)
frontend/   Phase 8: SvelteKit engineering workstation

scripts/    one demonstration/validation script per phase (phaseN_report.py),
            plus Phase 10's run_all_benchmarks.py and stress_test*.py
tests/      ~230 Python tests, plus backend/'s own Rust test suite (cargo test)
```

Data flow for a Pareto search, end to end: SvelteKit (in the browser) → Rust
`POST /api/pareto` (returns a job ID immediately, runs the search in a spawned
background task) → Python `POST /pareto` (plain HTTP) →
`apex.optimize.run_pareto_search()` → NSGA2 searching over `apex.design`'s
mass/cost buildup and `apex.physics`'s vehicle dynamics, with `apex.robust` and
`apex.surrogate`/`apex.active_learning` available the same way for the
requirements that use them. Every tier — the two web backends and the LLM
agent alike — calls into the same `apex` package; there is exactly one
implementation of "what a vehicle design means" and "what makes one feasible,"
not a Python copy and a Rust copy that could quietly drift apart.

### What's implemented

**Phase 1 — vehicle physics kernel**
- `src/apex/physics/longitudinal.py` — road-load equation (aero drag + rolling
  resistance + grade), tractive-force limits (torque-limited / power-limited /
  RPM-redline-limited motor regions, tire-traction ceiling).
- `src/apex/physics/performance.py` — 0-60 acceleration (forward time integration),
  top speed (force-balance root find), max gradeability, braking distance.
- `src/apex/physics/energy.py` — `simulate_drive_cycle()`: drive-cycle energy
  integration with a flat drivetrain/regen efficiency scalar (arbitrary speed-vs-time
  profile), `constant_speed_range_km()` steady-state approximation.
- `src/apex/physics/drive_cycles.py` — synthetic urban/highway speed profiles for
  feeding into the energy integrator (not reproductions of the official EPA traces —
  see the module docstring).
- `src/apex/physics/params.py` — `VehicleParams`, the design vector every other
  module operates on.

**Phase 2 — battery + motor efficiency**
- `src/apex/physics/battery.py` — SOC via Coulomb counting, terminal voltage via a
  single-resistor (Rint) equivalent circuit, C-rate- and thermally-derated
  charge/discharge current limits, a cycle-throughput capacity-fade proxy.
- `src/apex/physics/motor.py` — a physically-motivated efficiency map (fixed +
  copper + iron loss terms) replacing the flat scalar, referenced against
  `(peak_torque, base_speed)` where base_speed is where full torque meets rated
  power — see the module docstring for why that reference point matters and what
  broke when an earlier pass used the RPM redline instead.
- `src/apex/physics/energy.py` — `simulate_drive_cycle_with_battery()`: the same
  drive-cycle integration as Phase 1, but tracking actual SOC/voltage/current
  through the battery+motor models instead of a flat energy balance, including
  power-delivery clipping at the pack's current limits.

**Phase 3 — design-space representation + constraint system**
- `src/apex/design/variables.py` — `ContinuousVariable`/`DiscreteVariable`/`DesignSpace`:
  the mixed continuous+discrete space Phase 4's optimizer will search (a genuine
  MINLP flavor, not just a continuous relaxation).
- `src/apex/design/components.py` — named discrete-choice presets (motor
  architecture: PM synchronous/induction/switched-reluctance; battery chemistry:
  NMC/LFP; tire choice: eco/standard/performance) bundling the physical properties
  a real engineering decision carries together, web-verified mass/cost figures
  where a source exists (see the module docstring).
- `src/apex/design/candidate.py` — `DesignCandidate` (one point in the space) +
  `build_vehicle()`: the mass/cost buildup that operationalizes the platform's
  central MDO claim (battery ↔ mass ↔ range ↔ motor ↔ cost are coupled) by
  deriving mass, cost, and motor peak torque from the sizing decisions actually
  made, rather than letting them be independent free variables.
- `src/apex/design/constraints.py` — `Requirement`/`Mission`: engineering
  requirements (0-60 time, range, mass, gradeability, braking distance,
  manufacturing cost) evaluated against a built candidate via the Phase 1/2
  kernel, each returning a satisfied/violated verdict with a signed margin.
  Includes `example_crossover_mission()`, the platform proposal's own worked
  example ("a sub-$42k electric crossover capable of at least 310 miles of range
  while preserving 0-60 under six seconds").

**Phase 4 — multi-objective (Pareto) optimization**
- `src/apex/optimize/objectives.py` — `Objective`: named quantities to
  minimize/maximize (manufacturing cost, mass, 0-60 time, highway range), the
  same wrap-a-physics-call pattern as `design.constraints.Requirement`.
- `src/apex/optimize/problem.py` — `ArchitectureProblem`: a Phase 3
  `DesignSpace`+`Mission` wrapped as a pymoo mixed-variable `ElementwiseProblem`
  (`Requirement`s become inequality constraints, `Objective`s become the
  objective vector) — one representation of "optimizable" and "feasible" reused
  here, not duplicated in optimizer-specific form.
- `src/apex/optimize/pareto.py` — `run_pareto_search()`: NSGA2 with pymoo's
  mixed-variable operators (so Choice-type variables like motor architecture are
  searched natively, not one-hot-encoded), returning a structured
  `ParetoResult` of built vehicles and human-readable objective values.

**Phase 5 — Monte Carlo uncertainty + robust design**
- `src/apex/robust/uncertainty.py` — `Scenario`/`UncertaintyModel`: what varies
  across a vehicle's real service life (payload, ambient temperature, road grade,
  tire wear, battery state-of-health) and how it's sampled (independent uniform
  distributions — a documented simplification, not a measured distribution shape).
- `src/apex/robust/scenario_evaluation.py` — `apply_scenario()`: turns a Scenario
  into a scenario-adjusted `VehicleParams`+`BatteryState` (added payload mass,
  degraded rolling resistance/grip, battery-current-derated motor power, SOH-scaled
  usable energy), so every existing Phase 1-4 evaluator works completely unchanged
  on it — robustness lives entirely in *what vehicle gets passed in*.
- `src/apex/robust/robust.py` — `MonteCarloResult`, `RobustRequirement`/
  `RobustMission`: a chance-constrained relaxation of `g(x,u) <= 0 for all u` (
  "satisfied in >= `reliability_target` of sampled scenarios"), sharing each
  scenario's evaluation across every requirement rather than recomputing per
  requirement.
- `src/apex/robust/requirements.py` — `robust_crossover_mission()`, the robust
  counterpart of Phase 3's `example_crossover_mission()`.

Building this phase caught and fixed a real Phase 2 oversimplification: the
battery's thermal derating applied the same aggressive cold-weather power cut to
both charge *and* discharge, when real packs tolerate cold discharge (driving) far
better than cold charging (lithium plating is a charging-specific failure mode) —
see `physics/battery.py`'s `_thermal_derate_factor` docstring.

**Phase 6 — AI surrogate models**
- `src/apex/surrogate/features.py` — `encode_candidate()`/`feature_names()`:
  `DesignCandidate` <-> a flat numeric feature vector (continuous as-is, the
  ordinal `num_motors` as a plain number, the genuinely categorical discretes
  one-hot), derived from a `DesignSpace`'s own variable list rather than a
  hardcoded field order.
- `src/apex/surrogate/dataset.py` — `generate_dataset()`: Latin Hypercube
  Sampling on the continuous sub-space (far better space-filling coverage per
  sample than uniform random) crossed with an evenly-cycled sweep of discrete
  combinations, each point evaluated with the real Phase 1-4 physics kernel —
  this dataset *is* the ground truth the surrogates train against.
- `src/apex/surrogate/models.py` — `GPSurrogate`/`RandomForestSurrogate`:
  `fit(X,y)`/`predict(X) -> (mean, std)`. Gaussian Process Regression is the
  one that matters for what comes next — its analytic predictive uncertainty is
  exactly what Phase 7's active learning needs to pick the next design worth
  actually simulating; Random Forest is the comparison point (handles the mixed
  feature space natively, cheaper to fit, less principled uncertainty).
- `src/apex/surrogate/evaluate.py` — `train_and_compare()`: train/test split +
  per-target GP-vs-RF accuracy comparison, handing back fitted models ready for
  reuse.

`scripts/phase6_report.py` generates a 400-point dataset, fits both surrogate
types per target, and reports held-out accuracy (R² of 0.91-1.00 across cost/
mass/0-60/range — 0-60 is the hardest to fit, unsurprising given it comes from a
genuinely nonlinear numerical integration rather than a closed-form buildup
formula), a ~350x prediction-speed comparison against the real physics, and a
preview of the GP's uncertainty rising sharply for a point far outside the
training distribution — precisely the signal Phase 7 will use.

**Phase 7 — active-learning design-space exploration**
- `src/apex/active_learning/loop.py` — `select_next_index()`: the acquisition
  decision itself (highest predicted std for `"uncertainty"`, ignore the model
  entirely for `"random"`); `run_pool_based_learning()`: simulate the initial set
  → fit → predict pool uncertainty → pick → simulate → refit, repeated, tracking
  held-out R² at every step; `compare_strategies()` runs both selection
  strategies against an identical initial set/pool/held-out test set so any
  accuracy difference is attributable to the strategy, not to different data.
  Real physics is evaluated lazily, only for the specific candidate chosen each
  iteration — the loop is built to behave correctly if the underlying evaluator
  gets much more expensive later (a full CFD or FEA run), not just to work for
  this platform's fast kernel.

`scripts/phase7_report.py` runs both strategies against `zero_to_sixty_s` (Phase
6's hardest-to-fit target — the one place a smarter sampling strategy has room to
matter, versus the near-perfect-either-way cost/mass/range targets) and reports
an honest, seed-verified pattern: uncertainty sampling wins clearly in the
early-budget regime (the case that matters most for a genuinely expensive
simulator) but its lead erodes and typically reverses by the end of a longer
budget, because pure max-variance acquisition keeps re-choosing the design
space's edges (where a GP's predictive variance is structurally highest) rather
than covering its interior — a known limitation of the technique, not a bug.

**Phase 8 — Rust orchestration backend + SvelteKit workstation**

Three tiers, each with one job:
- `service/` (Python, FastAPI) — a thin, synchronous, blocking HTTP wrapper
  around the `apex` package: `/evaluate` (single candidate → mass/cost/0-60/
  range), `/pareto` (runs `optimize.run_pareto_search`), `/design-space` and
  `/requirement-kinds` (metadata so the frontend never hardcodes bounds/choices
  that live in `apex.design`). `mission_registry.py` is the one place a JSON
  `{"kind": "...", "threshold": ...}` list turns into real `Requirement` objects
  — Missions aren't JSON-serializable (they're Python closures over physics
  calls), so this translation has to happen somewhere at the HTTP boundary
  rather than being reinvented per endpoint.
- `backend/` (Rust, Axum) — routes the frontend's requests to the Python
  service. `/api/evaluate` and the metadata endpoints proxy synchronously
  (fast enough not to need more); `/api/pareto` is the reason this tier exists
  at all: it returns a job ID immediately and runs the actual (tens-of-seconds)
  NSGA2 search in a spawned background task, polled via `/api/pareto/:id` —
  exactly the "Rust... manage[s] simulations and orchestrate[s] jobs while
  Python runs the scientific workers" split the platform proposal describes.
  Vehicle/candidate/mission payloads are passed through as opaque JSON (see
  `handlers.rs`'s module doc) rather than duplicated as typed Rust structs —
  domain modeling of the physics/design space stays Python's job.
- `frontend/` (SvelteKit + TypeScript) — a single-page engineering-workstation
  MVP covering the proposal's core Generate → Optimize → Compare loop: a
  mission builder (reads valid requirement kinds from the backend), a "run
  search" action that starts a Pareto job and polls it to completion, a
  sortable results table, and a single-candidate evaluator whose form controls
  are generated from `/api/design-space`'s live bounds/choices rather than
  hardcoded. "inspect" on any Pareto point loads it straight into the
  evaluator. Verified working live through an actual browser session (not just
  `svelte-check`) — mission → search → polling → results → inspect → evaluate,
  full loop, real numbers matching the Python CLI reports exactly.

**Phase 9 — Vehicle Systems Engineer Agent**

Per the platform proposal: the agent "should not directly control optimization"
-- it can only affect the world through seven tools, every one of which calls
straight into the already-validated Phase 1-5 kernel. There is no eighth path
where the model just states a number.

- `agent/tools.py` — `TOOL_DEFINITIONS` (Anthropic tool-use JSON schemas, with
  numeric bounds and discrete choices read from `default_design_space()` at
  import time, never hardcoded) and `TOOL_DISPATCH`: `get_design_space`,
  `list_requirement_kinds`, `evaluate_candidate`, `check_mission` (per-requirement
  pass/fail with a signed margin -- "explain constraint violations"),
  `run_pareto_search`, `sensitivity_analysis` ("how does X change if I increase
  Y"), and `robust_check` (Phase 5's Monte Carlo checker, finally wired into
  something downstream, exactly the gap Phase 5's own README flagged).
- `agent/engineer_agent.py` — `run_agent_turn()`: a manual Claude tool-calling
  loop (not the beta Tool Runner, for full control over the forced-final-answer
  path). Defaults to `claude-opus-5` (overridable via `APEX_AGENT_MODEL`).
  **The forced-final-answer path uses `tool_choice: {"type": "none"}` with
  *lower effort*, not disabled thinking** -- current guidance is that disabling
  thinking on Claude Opus 5 has its own failure modes (a tool call can leak into
  visible text instead of a proper `tool_use` block), which is different from
  the "just disable thinking" fix that was correct for an older model
  generation; verified against the live API reference before writing this, not
  assumed from memory.
- `service/main.py`'s `POST /agent/chat` — single-turn only (no conversation
  history parameter): round-tripping raw Anthropic SDK content blocks through
  JSON for multi-turn persistence is real additional machinery this phase's
  scope didn't justify building half-finished. The route only registers if the
  `agent` extra is installed, so the core service (`/evaluate`, `/pareto`,
  metadata) never breaks because an optional dependency is missing.

**What's actually verified, and what isn't:** this environment has no
`ANTHROPIC_API_KEY`, so live model behavior was never observed. What *is*
tested without one: all seven tools against the real `apex` package (including a
test that JSON-serializes every tool's actual output -- exactly what the agent
loop does before sending a result back to Claude -- which is what caught a real
bug: `RequirementResult.satisfied` can be `numpy.bool_`, which the stdlib `json`
module can't serialize, unlike `numpy.float64`, which happens to subclass Python
`float` and silently works. That bug would have surfaced as a confusing
mid-conversation crash on `check_mission`'s or `robust_check`'s *second* real
use, not the first), and the loop's entire control flow (tool dispatch, message
threading, parallel tool calls answered in one message, `max_hops`, the forced-
final-answer path) against a fake Anthropic client built for exactly this.
`scripts/phase9_report.py` runs the proposal's own worked example against a real
model when credentials are available, and fails with a clear message instead of
a stack trace when they aren't.

**Phase 10 — benchmark validation, stress testing, clean acceptance, deployment**

- `scripts/run_all_benchmarks.py` — runs the Python test suite, the Rust test
  suite, `cargo clippy`, and the frontend typecheck, and prints one
  consolidated PASS/FAIL report with per-step timing. Not a new kind of
  testing — Phases 1-9 each already validate themselves individually; this is
  the first place all of it gets checked together in a single pass instead of
  nine separate ones nobody re-runs together.
- `tests/test_stress_boundaries.py` — every corner of the continuous design
  space (all 5 continuous variables simultaneously at their min or max bound,
  32 corners) crossed with the discrete choices, asserting finite, sane
  physics (no NaN, no negative mass/cost/time/range) at every one. Phases 1-6's
  tests validate *typical* designs extensively; an LHS sample essentially never
  lands exactly on a corner, so this specifically targets the *edges* of the
  declared valid domain, which nothing else exercises.
- `scripts/stress_test.py` — cumulative memory pressure from a realistic heavy
  sequence (three large Pareto searches, five robust checks, two surrogate
  dataset generations, surrogate training, an active-learning run) inside one
  long-running process, directly motivated by a documented incident in this
  user's sibling AirlinesApp project (several data-heavy endpoints hit in
  sequence within one warm process exhausting memory on a constrained host,
  even though each was fine alone). Result: RSS grew from 128.6MB to 137.4MB
  across the whole sequence (~7%) with no runaway/monotonic-leak pattern — a
  reassuring finding, checked proactively rather than found the hard way.
- `scripts/stress_test_concurrency.py` — fires several Pareto search jobs at
  the Rust backend at once, each with a *distinct* mission, and confirms not
  just that all jobs complete but that each job's result satisfies its own
  mission and not a neighbor's — the real risk in a shared
  `Arc<Mutex<HashMap>>` job store under concurrent access is silent
  cross-contamination, not a crash, so "didn't crash" alone wouldn't have
  caught it. Result: 6 concurrent jobs, 6 distinct IDs, zero contamination.
- **Clean-environment verification** (not a script — done directly this
  session): a brand-new Python venv, `pip install -e ".[dev,service,agent]"`,
  and the full 232-test suite, all passing with no dependency on any
  already-installed state; a full `cargo clean` + `cargo build` + `cargo test`
  from zero (1.1GiB removed, rebuilt in 2m18s, all 8 tests still passing); and
  a genuine SvelteKit production build (`npm run build`, switched from
  `adapter-auto` to `adapter-node` since auto couldn't detect a deployment
  target) with the resulting standalone server actually started and curl'd for
  a 200 — none of these had been checked from a truly clean state before this
  phase.
- `service/Dockerfile`, `backend/Dockerfile`, `frontend/Dockerfile`,
  `docker-compose.yml` — one Dockerfile per tier plus a compose file for
  one-command local startup. **Verified**: `docker compose up --build` builds
  all three images and runs a working app end to end (mission builder, Pareto
  search, single-candidate evaluate, and the agent chat panel all confirmed
  live through the containers in a real browser). The first build attempt did
  fail, for a real reason worth knowing about: `backend/Cargo.toml`'s
  `reqwest` dependency pulled in its default `native-tls` backend, which needs
  system OpenSSL + `pkg-config` -- neither present in the `rust:1-slim-bookworm`
  builder image. The fix wasn't installing those apt packages; it was noticing
  the Rust backend never actually makes an HTTPS request (it only ever talks
  plain HTTP to `scientific-service`, in-container or in dev) and switching to
  `rustls-tls` (`default-features = false`), which needs no system OpenSSL at
  all. Also found live: the native dev processes (`cargo run`, `uvicorn`) and
  the Docker containers bind the *same* host ports (8080/8001/3000) if both
  are running at once -- pick one or the other, don't run both.

### Running it

```bash
pip install -e ".[dev]"
pytest tests/ -v
python scripts/validate_report.py    # Phase 1: 0-60/top-speed/range vs. published specs
python scripts/phase2_report.py      # Phase 2: motor efficiency map + battery SOC trace
python scripts/phase3_report.py      # Phase 3: random-sampled candidates vs. the example mission
python scripts/phase4_report.py      # Phase 4: real NSGA2 Pareto frontier vs. the example mission (~1 min)
python scripts/phase5_report.py      # Phase 5: nominal-feasible designs re-checked under uncertainty (~1 min)
python scripts/phase6_report.py      # Phase 6: GP/RF surrogate accuracy + speed vs. real physics (~30s)
python scripts/phase7_report.py      # Phase 7: uncertainty-sampling vs. random-sampling learning curves (~1 min)
python scripts/phase9_report.py      # Phase 9: needs `pip install -e ".[dev,agent]"` + ANTHROPIC_API_KEY
python scripts/run_all_benchmarks.py # Phase 10: consolidated PASS/FAIL over pytest + cargo test/clippy + svelte-check
python scripts/stress_test.py        # Phase 10: cumulative memory pressure across a heavy operation sequence (~5 min)
```

**Phase 10, once the three services are running** (see below):

```bash
python scripts/stress_test_concurrency.py   # concurrent Pareto jobs, checks for job-store cross-contamination
```

**Deployment (verified, see the caveat above for what that first build caught):**

```bash
docker compose up --build
# then open http://localhost:3000
```

**Phase 8, three terminals** (each service needs the ones below it running):

```bash
# 1. Python scientific service (:8001)
pip install -e ".[dev,service]"
uvicorn service.main:app --port 8001

# 2. Rust orchestration backend (:8080) -- needs the Rust toolchain (rustup.rs)
cd backend && cargo test && cargo run

# 3. SvelteKit workstation (:5173)
cd frontend && npm install && npm run dev -- --port 5173
```
Then open `http://localhost:5173`. `backend/` also has its own test suite
(`cargo test`, 8 tests: 4 unit + 4 integration against a real router via
`tower::ServiceExt::oneshot`) and passes `cargo clippy` with zero warnings.

`tests/reference_vehicles.py` holds the published specs (Tesla Model 3 LR AWD, Chevy
Bolt EV, Nissan Leaf) used for validation, web-verified against multiple sources, along
with a docstring on why the tolerances in `tests/test_validation.py` are intentionally
generous — this kernel checks "right ballpark, right shape of physics," not "matches
the dyno sheet," since it has no manufacturer efficiency map or real transmission data.

### Known simplifications (by design)

**Phase 1**
- Traction is assumed available to the full vehicle mass (i.e. AWD); a front/rear
  weight-transfer model belongs to the lateral vehicle-dynamics layer (bicycle model),
  not this longitudinal kernel.
- No electronic top-speed governor — Tesla's real top speed is a software cap (likely
  tire speed rating) below both its power- and RPM-redline-limited physics ceilings;
  the kernel reports the physics limit, which is why that one reference vehicle's
  top-speed check has more slack than the Bolt/Leaf (whose governed top speed sits
  right at their RPM redline, and matches closely).
- `constant_speed_range_km` is a steady-state reference point, not an EPA-equivalent
  range (EPA uses a weighted multi-cycle test procedure with a real-world adjustment
  factor).

**Phase 2**
- Battery pack temperature is an exogenous input per call, not evolved from the
  pack's own I²R heat generation — self-heating/cooling dynamics are a natural
  further deepening, not included yet.
- The motor efficiency map is one representative "good EV traction motor" shape
  (fixed/copper/iron loss fractions tuned to real reference-vehicle range figures),
  not any specific motor's dyno map. It also doesn't model a multi-motor vehicle
  disengaging one motor at light load (a real Tesla dual-motor behavior).
- `battery_internal_resistance_ohm` and the C-rate limits in `VehicleParams` are
  generic plausible defaults, not vehicle-specific — no manufacturer publishes those.
- The capacity-fade proxy (`battery_fade_per_1000_ah_throughput`) is a simple linear
  throughput model, not a physically validated aging model (real fade depends on
  temperature history and calendar time too) — a placeholder for the later
  reliability/robust-design phases to build on.

**Phase 3**
- No packaging/volume model — passenger and cargo volume aren't represented, so
  there's no requirement constructor for them (see `constraints.py`'s docstring for
  the full list of what's deliberately not offered yet: volume, lateral stability,
  component reliability, sustainability targets).
- `PlatformContext`'s glider mass/cost (~950kg, ~$19k) are order-of-magnitude
  planning figures for one representative "compact crossover" platform, not sourced
  from any real vehicle's bill of materials — everything the design space actually
  varies (battery, motor, tires) is buildup-derived and separately sourced; the
  fixed remainder isn't.
- `example_crossover_mission()`'s $42k target is treated as MSRP and converted to a
  manufacturing-cost cap via a documented ~1.4x markup factor, since this platform
  has no pricing-structure model — using $42k directly as a manufacturing-cost cap
  would have been a materially easier (and unrealistic) constraint.
- Discrete motor-architecture choices affect mass/cost/RPM-redline/base-speed/flat
  efficiency scalars, but not motor.py's loss-shape coefficients (still one generic
  map for all three architectures) — a deeper per-architecture efficiency map is a
  natural refinement, not done yet.

**Phase 4**
- Objectives are limited to what Phases 1-3 can actually compute (cost, mass, 0-60
  time, range) — not the platform proposal's full [Cost, Energy, Mass, ThermalRisk]
  / [Range, Performance, SafetyMargin, RideQuality] list. ThermalRisk, SafetyMargin,
  and RideQuality would all need models this repository doesn't have yet (see
  `optimize/objectives.py`'s docstring); adding objective functions for them now
  would mean inventing numbers to optimize against.
- Only NSGA2 (evolutionary multi-objective search) is implemented. The platform
  proposal's software stack also names CasADi/IPOPT (continuous gradient-based NLP)
  and OR-Tools CP-SAT (discrete/scheduling-style optimization) — NSGA2 alone
  already handles this phase's mixed continuous/discrete, multi-objective,
  constrained problem end to end, so those weren't needed to deliver "nonlinear and
  multi-objective optimization," but a gradient-based refinement pass on top of a
  promising NSGA2 result is a natural next step, not done yet.
- Requirement margins feed pymoo's constraint vector unnormalized, across wildly
  different units (USD, seconds, miles, kg) — NSGA2's feasibility-first dominance
  handles this correctly, but per-constraint normalization would likely improve
  search efficiency; not done yet.
- No robustness: each candidate is evaluated at one nominal operating point (25°C,
  flat road, no payload). Uncertainty in temperature/grade/payload/degradation is
  Phase 5 (robust optimization) per the roadmap, not this phase.

**Phase 5**
- `RobustMission`/`RobustRequirement` are a chance-constrained *relaxation* of the
  formal `g(x,u) <= 0 for all u in U` robust statement, not a calibrated
  probability-of-failure model — the platform proposal's own text explicitly calls
  full Reliability-Based Design Optimization (`P[g_i(x,xi) <= 0] <= eps_i`) a
  *later* phase, not this one.
- Uncertainty distributions are independent uniforms over documented ranges, not
  measured or correlated distributions (e.g. cold weather and higher payload
  probably co-occur in reality — a winter road trip — but are sampled
  independently here). Ambient temperature's wide uniform range in particular
  (-20C to 40C) means roughly half of sampled scenarios see *some* cold-weather
  battery derating, more pessimistic than a real seasonal-weighted distribution —
  see `scripts/phase5_report.py`'s output for what this does to failure rates.
- Wind and driver behavior, both named in the platform proposal's uncertainty
  list, aren't modeled — no mechanism in this kernel to apply them distinctly
  from the five parameters that are.
- `RobustMission` isn't wired into Phase 4's optimizer — `scripts/phase5_report.py`
  demonstrates that random nominal-nominal-optimal sampling essentially never
  finds a robust-feasible design (Phase 4's cost-minimizing search hugs the
  feasibility boundary with no margin), and that a deliberately generously-margined
  design does hold up, but finding robust designs *automatically* means feeding
  RobustMission into the optimizer as its constraint set instead of checking
  robustness only after the fact. That integration is the natural next step, not
  built in this phase.
- Battery-current-limited motor power (the mechanism that makes cold weather and
  low SOH actually cost acceleration) only applies within `apply_scenario()`'s
  pathway -- Phase 1-4's plain evaluators still never consult the battery's
  current limits, by design (see `energy.py`'s module docstring for why the two
  paths coexist).

**Phase 6**
- Surrogates predict Phase 4's four objectives only (cost, mass, 0-60 time,
  range) — not Phase 5's robust/Monte-Carlo-derived quantities. A surrogate for
  "fraction of scenarios satisfying a requirement" would need training data from
  repeated Monte Carlo runs (expensive to generate), and isn't built here.
- The dataset is generated once per script run, at one fixed `PlatformContext`
  (the same default compact-crossover glider Phase 3 always uses) — a surrogate
  trained here doesn't generalize to a different platform without regenerating
  the dataset against it.
- `GPSurrogate`'s kernel is a single global RBF over standardized features — one
  length-scale per dimension isn't fit (no automatic relevance determination),
  so it can't automatically discover that some inputs matter far more than
  others for a given target. Given how cleanly R² already lands (0.91-1.00), a
  richer kernel wasn't needed to make this phase's point, but is a natural
  refinement if a much higher-dimensional design space is added later.
- No hyperparameter search beyond scikit-learn's defaults (RF's `n_estimators`,
  GP's kernel bounds) — tuned enough to make the comparison meaningful, not
  exhaustively optimized.
- `RandomForestSurrogate`'s tree-spread "uncertainty" is a real, useful signal
  but not a calibrated predictive distribution the way the GP's is — treat it as
  a rough proxy, not an interval with a stated confidence level.

**Phase 7**
- Pure "highest predicted std" (max-variance) acquisition, no diversity term —
  the demonstrated, seed-verified consequence is that it repeatedly re-chooses
  the design space's edges rather than covering the interior, which is why its
  early-budget advantage erodes and typically reverses over a longer run (see
  `scripts/phase7_report.py`'s output). Blending in a diversity penalty (so
  already-well-covered regions score lower even if locally uncertain) is the
  standard fix in the active-learning literature and a natural next refinement,
  not built here.
- The active-learning loop only targets one output at a time (pass a single
  `target_index`) — it doesn't jointly optimize sampling for all four Phase 4
  objectives at once, which would need a multi-output acquisition function
  (e.g. maximize total predictive variance across targets, or query-by-committee
  across per-target models) rather than this phase's single-target uncertainty.
- Each iteration refits the GP from scratch on the full accumulated training set
  rather than warm-starting or using an online/incremental update — fine at this
  scale (well under a second per refit up to ~60 points), but wouldn't scale to
  a training set of thousands without a smarter update strategy.
- `run_pool_based_learning()` isn't wired into Phase 4's optimizer or Phase 5's
  robust-mission checking — it improves a *surrogate's* accuracy for one target,
  which is a different (upstream) concern from searching the design space or
  checking robustness with whatever surrogate currently exists. Connecting them
  (e.g. running NSGA2 against a surrogate refined by active learning instead of
  the real physics kernel directly) is a natural next step, not built here.

**Phase 8**
- The frontend covers one workflow slice (Mission → Generate → Optimize →
  Compare, plus single-candidate Evaluate) of the platform proposal's full
  product experience (Design Space Explorer, Pareto Laboratory, an engineering
  dossier per selected design, a Stress Lab running Phase 5's robust checks
  interactively) — a deliberate MVP scope, not the whole workstation.
- No automated frontend tests (no Vitest/Playwright) — verified instead by
  `svelte-check` (0 errors) plus a real, manual, tool-driven browser session
  exercising every interactive path (mission edit → search → poll → results →
  inspect → evaluate) against the live Rust+Python stack. Real automated
  browser tests are a natural next step for a frontend meant to keep growing.
- The Rust job store is in-memory with no TTL/eviction (documented in
  `jobs.rs`) — fine for a dev/demo server, would leak memory over a long-running
  production deployment without an eviction policy.
- CORS on the Rust backend is fully permissive (`Any` origin) — appropriate for
  a local orchestration layer with nothing sensitive behind it, not for a
  public-facing deployment.
- The Python service is synchronous/blocking by design (see its module doc) —
  concurrency for multiple simultaneous `/pareto` requests depends on uvicorn's
  default threadpool sizing for sync `def` handlers, not on anything this phase
  tuned explicitly.
- Neither NATS (the proposal's suggested job-queue transport) nor PyO3-embedded
  Python is used — Rust talks to Python over plain HTTP (`reqwest`), and job
  state lives in an in-memory `HashMap`. This is a substantially lighter-weight
  realization of "Rust orchestrates, Python computes" than the proposal's full
  event-driven architecture, chosen to be buildable, testable, and genuinely
  run end to end in one phase rather than left half-wired.

**Phase 9**
- **Live model behavior is now verified** -- once a real ANTHROPIC_API_KEY was
  set, two real requests were run through the browser against the Docker
  stack. A simple one ("what battery capacities are possible?") answered
  correctly off a single `get_design_space` call. A hard one ("cheap design
  under $28k that still does sub-6s 0-60") took 16 tool calls -- a real NSGA2
  Pareto search, then the agent *unprompted* ran Monte Carlo robust checks and
  found that every nominally-cheap sub-6s design has a 0% robust pass rate
  (6.5-7.9s realistic 0-60, not the 3.9-5.8s nominal figures) -- correctly
  distinguishing "looks good on paper" from "holds up under uncertainty"
  without being asked to. It hit `max_hops` and got force-finalized, and still
  produced a complete, well-reasoned, honestly-caveated answer rather than
  truncating or returning nothing -- confirming the `force_final` +
  `thinking: adaptive` interaction (see `agent/engineer_agent.py`'s module
  doc) behaves correctly under real multi-hop load, not just in mocked tests.
  `scripts/phase9_report.py`'s own harder prompt then hit a real account-level
  wall (`anthropic.BadRequestError: ... credit balance is too low`) rather
  than a code bug -- likely from the 16-tool-call request above, which used
  real tokens across many round-trips of adaptive thinking. Treat the two
  browser-verified requests as confirming the mechanism works; a fuller sweep
  (does it correctly say "no" when a design truly fails `robust_check`, etc.)
  still needs `scripts/phase9_report.py` run with a funded key.
- `/agent/chat` is single-turn only -- no server-side conversation/session
  store, so each HTTP call is a fresh `run_agent_turn()` with no memory of
  earlier turns. `run_agent_turn()` itself supports a `history` parameter for
  multi-turn use (see `agent/engineer_agent.py` and
  `tests/test_agent_loop.py::test_conversation_history_threads_across_turns`)
  -- only the HTTP boundary doesn't expose it yet.
- Now wired into the Rust backend (`POST /api/agent/chat`, plain proxy) and the
  SvelteKit frontend ("4. Ask the engineer agent" panel) -- added after Phase
  10, once it became clear the agent was fully built and tested but had no way
  to actually reach it from the app. Verified live through a real browser
  against both the dev servers and the Docker containers, but only the
  no-API-key path (a clean 401) -- still no ANTHROPIC_API_KEY in this
  environment, so an actual model response has still never been observed.
- `run_pareto_search`'s tool defaults (pop_size=30, n_gen=10) are lower than
  the CLI reports' defaults (Phase 4 used 80/30) -- sized for "returns within a
  chat turn," not search thoroughness; the agent can request a larger search
  explicitly (both are exposed, bounded, tool parameters) when it matters.
- `sensitivity_analysis` only varies one field at a time -- no interaction
  effects between two simultaneously-varied fields, which is a real limitation
  for questions like "how do battery capacity and motor power trade off
  together" (that's closer to what `run_pareto_search` already answers, just
  not in a single-axis sensitivity-sweep format).
- Tool JSON-serialization is covered by
  `test_every_tool_result_is_json_serializable`, added specifically because it
  caught the `numpy.bool_` bug described above -- but that test enumerates
  representative inputs per tool, not an exhaustive sweep of the input space;
  a field this test doesn't exercise could still hide a similar numpy-type leak.

**Phase 10**
- Docker builds are now verified (see this phase's own section above for the
  real bug the first build attempt caught and how it was fixed) -- run through
  `docker compose up --build` with all three containers checked live in a
  real browser, not just built.
- Both stress tests have now been re-run **inside the actual Docker
  containers**, not just the native dev processes:
  - `stress_test.py`: baseline 129.5MB -> 159.0MB RSS, plateauing entirely
    after the surrogate-training step -- the 106.7s / 40-iteration
    active-learning phase that follows shows *zero* further growth, the
    clearest possible signal against a monotonic leak. (Caught along the way:
    `psutil` -- this script's only non-stdlib import -- was never actually
    declared in `pyproject.toml`'s `dev` extras; it happened to already be in
    this session's venv from being installed by hand in Phase 10. A genuinely
    clean `pip install -e ".[dev]"` would have failed this script immediately.
    Fixed by adding it to `dev`.)
  - `stress_test_concurrency.py`: unmodified, since it already targets
    `127.0.0.1:8080` -- transparently exercised the Docker containers once
    they were the thing listening there. 6 concurrent jobs, 7.1s, zero
    cross-contamination.
  - `restart: unless-stopped` was checked against two different failure
    modes, since they're not the same thing: `docker kill` on the backend
    container did *not* auto-restart it (`RestartCount` stayed 0, container
    sat `Exited (137)`) -- correct behavior, since an externally-issued
    kill/stop is Docker's signal that a human wants the container down, and
    every restart policy (including `always`) respects that. Sending SIGKILL
    to PID 1 *from inside* the container (`docker exec ... sh -c 'kill -9
    1'`), simulating an actual crash, *did* trigger an automatic restart --
    confirmed via a fresh `StartedAt` timestamp and a passing health check
    moments later.
  - The memory stress test checks one process running a heavy sequence for a
    few minutes, not a genuinely long-running production service over
    hours/days, and not multiple concurrent Python worker processes under
    real request load -- a real production deployment's memory profile could
    still differ, especially under sustained concurrent `/pareto` traffic
    (uvicorn's default threadpool sizing for sync `def` handlers, not tuned
    here -- see Phase 8's known simplifications).
  - The concurrency stress test checks 6 simultaneous jobs once, not a
    sustained load test with many more concurrent clients or a longer
    duration -- it demonstrates the job store's isolation is *correct*, not
    that it scales to arbitrary concurrency.
- The design-space boundary stress test checks the 32 continuous corners
  crossed with a subset of discrete combinations (cycled, not fully crossed --
  see the test file's docstring for why full crossing wouldn't find anything
  extra), and checks for *finiteness/sanity*, not for physical *accuracy* at
  the boundaries -- Phase 1's reference-vehicle validation is what checks
  accuracy, this checks the kernel doesn't fall over at the edges of its
  declared domain.
- No load/performance benchmarking beyond what the stress tests above cover
  (no p50/p95/p99 latency numbers, no throughput ceiling, no profiling) --
  "does it stay correct and not leak under a heavy sequence" was this phase's
  question, not "how many requests/second can it sustain."
- `run_all_benchmarks.py` gates Python tests, Rust tests, `cargo clippy`, and
  the frontend typecheck -- it does not run a live `npm run build`, the
  stress-test scripts, or (for obvious reasons) the Docker builds; those stay
  separate, slower, and in the concurrency case, dependent on services already
  running, rather than folded into one "everything" command.

## Enterprise operability gate

This source release includes a governed decision-assurance layer, negative-path operability tests, hash-verifiable evidence, and a Windows enterprise acceptance gate. See `docs/ENTERPRISE_OPERABILITY.md`.

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\\scripts\\windows_enterprise_acceptance.ps1
```


## Public Data Backbone
This release contains a structured public-data layer under `data/raw`, `data/processed`, `data/contracts`, `data/dictionaries`, `data/provenance`, and `data/snapshots`. Run `scripts\fetch_public_data_windows.ps1` when the primary public dataset is not bundled, then run `scripts\windows_real_data_acceptance.ps1`. `artifacts/data_backbone_status.json` records source state, row/feature counts, missingness, SHA-256, validation status, case-study state, claim boundary, model version, and the human decision authority.

The public-data case is `Tesla Model Y Benchmark-Calibrated Architecture Study` and is wired into `ARCH-SHIELD-v1` review. Missing external raw data never silently falls back to a real-data claim; the dossier explicitly enters `REFERENCE_MODE_HOLD_FOR_REAL_DATA_CLAIM`.
