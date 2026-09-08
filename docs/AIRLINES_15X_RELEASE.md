# APEX V1 — Airlines-1.5× Depth Candidate

Release: `APEX_V1_FORTUNE50_AIRLINES15X_RC4`

## What changed

This release adds a provenance-aware empirical backbone, a live empirical API, project-native historical/entity diagnostics, a named empirical case study, external-source refresh/promotion workflow, live empirical charts, and a 26+ workspace contract in which each workspace has a distinct method/evidence/action definition.

## Current evidence mode

- Source: **2025 Automotive Trends — MY2024 Fuel Economy & Technology Data**
- Source URL: https://www.epa.gov/automotive-trends/explore-automotive-trends-data
- Mode: **offline_reference**
- Promotion state: **REFERENCE_ONLY**
- Local analyzable evidence: **70 rows / 3 fields**
- Workspaces: **27**

## Domain diagnostic

**robust architecture confidence/cost frontier**

Reference metrics:
```json
{
  "scenario_samples": 300,
  "candidate_designs": 4,
  "confidence_certified_designs": 2,
  "robustness_premium_vs_cheapest_usd": 11067.0
}
```

Decision signal: ARCH-SHIELD may pay a manufacturing-cost premium when finite-sample reliability confidence rejects a cheaper nominal design.

## Analytical chain

source provenance → schema/data-quality checks → entity/factor drilldown → cohort/history comparison → diagnostic ranking → predictive model → original algorithm → OR/simulation escalation → counterfactual challenge → human decision

## Windows gates

Core/offline acceptance:
```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows_airlines15x_acceptance.ps1
```

External-data promotion (internet required):
```powershell
.\scripts\windows_external_data_promotion.ps1
```

## Claim boundary

External-source results are claimed only when data_mode is refreshed_external or published_external_snapshot; offline_reference remains reference evidence.

The label “Airlines-1.5×” is an internal portfolio-depth target relative to the latest observable Airlines evidence, not an external company certification and not a claim that reference/synthetic data is real production evidence.
