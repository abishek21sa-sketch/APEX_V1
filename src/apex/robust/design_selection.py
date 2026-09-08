"""APEX-RDS: robust design selection over a shortlisted architecture set.

Nominal Pareto optimality is not enough for an engineering release decision. APEX-RDS
re-evaluates every shortlisted design on the *same* uncertainty scenarios (common
random numbers), measures reliability shortfall and normalized constraint violation,
then selects lexicographically:

1. robust feasibility,
2. total reliability-target shortfall,
3. upper-tail CVaR of scenario violation,
4. mean violation,
5. manufacturing cost.

This prevents a small nominal cost saving from outranking a design that actually
meets the governed robust requirements.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable
from statistics import NormalDist
import numpy as np

from .robust import RobustMission
from .scenario_evaluation import evaluate_under_scenario
from ..design import DesignCandidate, Direction, PlatformContext, build_vehicle


@dataclass(frozen=True)
class RobustDesignScore:
    candidate_index: int
    manufacturing_cost_usd: float
    robustly_feasible: bool
    reliability_shortfall: float
    mean_normalized_violation: float
    cvar_normalized_violation: float
    worst_normalized_violation: float
    requirement_reliability: dict[str, float]
    requirement_reliability_lower_bound: dict[str, float]
    requirement_targets: dict[str, float]
    confidence_certified: bool


def _cvar(values: np.ndarray, alpha: float) -> float:
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be between 0 and 1")
    if len(values) == 0:
        return 0.0
    q = float(np.quantile(values, alpha))
    tail = values[values >= q - 1e-15]
    return float(np.mean(tail)) if len(tail) else q


def _normalized_violation(direction: Direction, value: float, threshold: float) -> float:
    scale = max(abs(float(threshold)), 1e-9)
    if direction is Direction.AT_MOST:
        return max(0.0, (float(value) - threshold) / scale)
    return max(0.0, (threshold - float(value)) / scale)



def _wilson_lower_bound(successes: int, n: int, confidence: float = 0.95) -> float:
    """One-sided Wilson lower confidence bound for a Bernoulli reliability.

    The point estimate alone is too optimistic for an engineering release gate.
    A design is confidence-certified only when the lower bound meets every
    governed reliability target.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if not 0.5 < confidence < 1.0:
        raise ValueError("confidence must be between 0.5 and 1")
    z = NormalDist().inv_cdf(confidence)
    phat = successes / n
    denom = 1.0 + z * z / n
    center = (phat + z * z / (2.0 * n)) / denom
    margin = z * np.sqrt((phat * (1.0 - phat) + z * z / (4.0 * n)) / n) / denom
    return float(max(0.0, center - margin))


def evaluate_shortlist(
    candidates: Iterable[DesignCandidate],
    mission: RobustMission,
    *,
    n_samples: int = 300,
    seed: int = 2026,
    cvar_alpha: float = 0.90,
    context: PlatformContext = PlatformContext(),
    confidence: float = 0.95,
) -> list[RobustDesignScore]:
    candidates = list(candidates)
    if not candidates:
        raise ValueError("at least one candidate is required")
    if n_samples < 10:
        raise ValueError("n_samples must be at least 10")
    rng = np.random.default_rng(seed)
    # Common random numbers are a deliberate variance-reduction / fair-comparison device.
    scenarios = mission.uncertainty_model.sample_many(n_samples, rng)
    scores: list[RobustDesignScore] = []
    for idx, candidate in enumerate(candidates):
        vehicle, report = build_vehicle(candidate, context)
        scenario_results = [evaluate_under_scenario(vehicle, s, mission.highway_speed_mps) for s in scenarios]
        per_scenario = np.zeros(n_samples, dtype=float)
        reliabilities: dict[str, float] = {}
        reliability_lbs: dict[str, float] = {}
        targets: dict[str, float] = {}
        shortfall = 0.0
        robust_feasible = True
        confidence_certified = True
        for req in mission.requirements:
            values = np.array([float(req.metric(sr)) for sr in scenario_results], dtype=float)
            if req.direction is Direction.AT_MOST:
                passed = values <= req.threshold
            else:
                passed = values >= req.threshold
            successes = int(np.count_nonzero(passed))
            reliability = float(successes / n_samples)
            reliability_lb = _wilson_lower_bound(successes, n_samples, confidence)
            reliabilities[req.name] = reliability
            reliability_lbs[req.name] = reliability_lb
            targets[req.name] = float(req.reliability_target)
            shortfall += max(0.0, float(req.reliability_target) - reliability_lb)
            robust_feasible = robust_feasible and reliability >= float(req.reliability_target)
            confidence_certified = confidence_certified and reliability_lb >= float(req.reliability_target)
            violations = np.array([
                _normalized_violation(req.direction, v, float(req.threshold)) for v in values
            ])
            # The worst active requirement governs a scenario's design-violation severity.
            per_scenario = np.maximum(per_scenario, violations)
        scores.append(RobustDesignScore(
            candidate_index=idx,
            manufacturing_cost_usd=float(report.total_manufacturing_cost),
            robustly_feasible=bool(robust_feasible),
            reliability_shortfall=float(shortfall),
            mean_normalized_violation=float(np.mean(per_scenario)),
            cvar_normalized_violation=_cvar(per_scenario, cvar_alpha),
            worst_normalized_violation=float(np.max(per_scenario)),
            requirement_reliability=reliabilities,
            requirement_reliability_lower_bound=reliability_lbs,
            requirement_targets=targets,
            confidence_certified=bool(confidence_certified),
        ))
    return scores


def select_robust_design(
    candidates: Iterable[DesignCandidate],
    mission: RobustMission,
    *,
    n_samples: int = 300,
    seed: int = 2026,
    cvar_alpha: float = 0.90,
    confidence: float = 0.95,
) -> dict:
    candidates = list(candidates)
    scores = evaluate_shortlist(candidates, mission, n_samples=n_samples, seed=seed, cvar_alpha=cvar_alpha, confidence=confidence)
    def key(s: RobustDesignScore):
        return (
            0 if s.confidence_certified else 1,
            0 if s.robustly_feasible else 1,
            round(s.reliability_shortfall, 12),
            round(s.cvar_normalized_violation, 12),
            round(s.mean_normalized_violation, 12),
            s.manufacturing_cost_usd,
            s.candidate_index,
        )
    chosen = min(scores, key=key)
    return {
        "method": "APEX-RDS lexicographic robust design selection with common random numbers",
        "selected_index": chosen.candidate_index,
        "selected_candidate": candidates[chosen.candidate_index].as_dict(),
        "selected_score": asdict(chosen),
        "scores": [asdict(s) for s in scores],
        "n_samples": n_samples,
        "seed": seed,
        "cvar_alpha": cvar_alpha,
        "reliability_confidence": confidence,
        "decision_policy": "Finite-sample confidence certification dominates point-estimate robust feasibility; reliability shortfall and tail violation dominate mean violation; manufacturing cost is used only after safety/performance robustness criteria.",
        "evidence_boundary": "Scenario robustness is model-based engineering evidence, not real-world vehicle validation or certification.",
    }
