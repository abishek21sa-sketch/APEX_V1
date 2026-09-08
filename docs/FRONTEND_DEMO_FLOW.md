# Frontend Demo Flow — APEX V1 — EV Architecture Decision Intelligence

This product keeps its own visual language: **EV systems-design studio / architecture schematic**. The shared contract is behavioral evidence, not a shared layout or theme.

## Native entrypoint

`frontend/src/routes/robust/+page.svelte`

## Project-specific demo sequence

1. inspect vehicle architecture
2. run robust reliability gate
3. compare baseline and counterfactual
4. review saved design certificate
5. approve architecture review

## Evidence requirements

The screen must show the project-native inputs, objective, constraints, baseline/counterfactual, evidence class, signature decision, and human approval/hold state. The product must not imply autonomous actuation.

## API evidence surface

The read-only signature evidence endpoint is `/governance/signature`. Its response is linked to `artifacts/fortune50_capability_benchmark.json` and exposes the current decision, baseline, sensitivity/counterfactual evidence, and human-gated status.
