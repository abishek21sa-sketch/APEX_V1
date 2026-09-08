# ARCH-SHIELD-v1 — Signature Algorithm Contract

This document is the project-native mathematical center required by the portfolio governance pack. The implementation alias is **robust architecture selection**.

## Operational decision

The module makes one operational decision: **select a vehicle architecture that satisfies range, acceleration, cost, and reliability gates**.

## Mathematical center

- **Decision variables:** discrete architecture candidate choice; cost, range, acceleration, and reliability are candidate parameters.
- **Objective:** minimize cost, then prefer higher reliability and range.
- **Constraints and release gates:** range >= minimum; 0-60 time <= maximum; cost <= budget; reliability >= floor.
- **Determinism:** the reference contract is deterministic for a fixed candidate set, scenario, and seed.
- **Solver status:** the current reference is an executable enumerative/closed-form contract; production solver integration remains downstream of this gate.

## Baseline and counterfactual

The named baseline is **cheapest feasible architecture without the reliability gate**. The counterfactual is evaluated on the same inputs and scenario so that a claimed improvement cannot be caused by a changed data slice.

## Ablation

The declared ablation is to **remove the reliability floor while retaining the other feasibility gates**. It is executable through the module's `ablation(...)` function and is covered by the signature tests.

## Sensitivity

The sensitivity sweep is: **vary the cost ceiling and reliability floor; record feasibility and selected architecture**. Sensitivity output is evidence about robustness, not a claim of causal production impact.

## Evidence classes and authority

Evidence is kept separate as observed, simulated, optimized, shadow-mode, and realized. **observed public vehicle data for inputs; simulated scenario analysis for release behavior; no realized production claim** A human authority remains required before any operational action; autonomous execution is disabled.

## Implementation and acceptance

- Implementation: `src/apex/robust/signature_algorithm.py`
- Windows acceptance test: `tests/test_signature_algorithm.py`
- Required acceptance result: `4 tests, OK`, with invalid inputs and no-feasible cases controlled explicitly.

## Release boundary

This signature is release-ready only when this contract, the research-validation protocol, the machine-readable governance artifact, the existing Airlines 1.5x gates, and the final integrity/hash checks all pass together.
