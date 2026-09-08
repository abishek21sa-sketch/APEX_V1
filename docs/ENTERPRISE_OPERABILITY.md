# Enterprise Operability & Decision Assurance

**Release:** `APEX_V1_ENTERPRISE_RC2`  
**Phase:** Enterprise operability and decision assurance  
**Primary target:** Windows  

## Decision authority

The analytical engine may recommend, rank, simulate, or optimize, but this release does **not** grant autonomous production authority. The governing human authority is **Vehicle systems engineer / design review board** and the execution mode is **ENGINEERING_REVIEW_ONLY**.

## What this phase hardens

- Tamper-evident or hash-verifiable decision evidence.
- Explicit PASS/HOLD/review states instead of implicit action.
- Negative-path validation for malformed, unsafe, infeasible, weak-evidence, or tampered inputs.
- Request correlation / execution-boundary headers on decision APIs where an HTTP surface exists.
- A project-native enterprise-operability runner that exercises both the decision core and governance boundary.
- Regression evidence separated from native/polyglot or external-validation gates.

## Verified regression

- Passed: **222**
- Skipped in this environment: **17**
- Failures/errors: **0 / 0**
- Scope: Available-dependency Python suite; 17 dependency-gated tests explicitly skipped here

## Windows enterprise gate

Run from a clean extraction in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\\scripts\\windows_enterprise_acceptance.ps1
```

The Windows gate is intentionally stricter than the container evidence and must install/run project-native dependencies where applicable.

## Evidence boundary

Included numerical validation is deterministic/synthetic/model-based unless a source explicitly states otherwise. It must not be presented as real-factory, real-grid, real-vehicle-production, or clinical outcome validation.

## Gates still pending

- pymoo NSGA-II/Pareto tests on Windows after declared dependency installation
- Optional Anthropic agent integration tests with agent extra
- Rust backend cargo tests
- Frontend npm clean build
- Physical/CAE/prototype validation before design release
