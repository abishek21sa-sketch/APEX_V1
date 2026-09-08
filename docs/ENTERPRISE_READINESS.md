# Enterprise Readiness — APEX V1

## Release status

**APEX_V1_PORTFOLIO_RC1** is a portfolio release candidate, not a production deployment certification.

## Decision-system identity

Selects vehicle architecture from physics/Pareto candidates using common uncertainty scenarios and confidence-bounded reliability before manufacturing cost.

**Signature core:** Physics-based EV architecture optimization + APEX-RDS finite-sample robust design selection

## Verified in this recovery build

- 200/200 dependency-independent Python core/service tests verified
- Machine-readable validation evidence is included and hashed.
- Production writes/autonomous execution are blocked by release governance.
- Windows remains the primary local acceptance target.

## Evidence inventory

- `artifacts/portfolio_validation.json` — SHA-256 `bb06a2253011e4b2a9aea0cba8f4891d4e02fb1c77f6a3e9f028b1ca223d316c`

## Gates still required before any production claim

- NSGA-II/Pareto tests after installing declared pymoo dependency
- Anthropic agent tests when optional agent extra is installed
- Windows frontend/backend integration acceptance
- External vehicle/track/thermal validation

## Claim boundary

This repository may be presented as a reproducible engineering/research decision system supported by its included model-based evidence. It must not be presented as real-world production improvement, certification, clinical effectiveness, vehicle certification, grid approval, or plant/fab performance unless that external validation is subsequently completed.
