"""Monte Carlo uncertainty propagation and a chance-constrained relaxation of
robust design's formal statement:

    g(x, u) <= 0   for all u in the uncertainty set U

Checking literally every u is impossible with continuous uncertainty and Monte
Carlo sampling; the practical relaxation used here is a chance constraint --
"g(x, u) <= 0 for at least `reliability_target` of sampled u" -- which is Phase
5's job per the roadmap ("Add Monte Carlo uncertainty and robust design
optimization"). A calibrated per-requirement failure-probability target
(P[g_i(x, xi) <= 0] <= eps_i, formal Reliability-Based Design Optimization) is
explicitly a *later* phase in the platform proposal's own text, not this one --
RobustRequirement's reliability_target is a simpler, uncalibrated version of the
same idea.

RobustMission.evaluate() computes each sampled scenario's ScenarioResult exactly
once and shares it across every requirement, rather than each requirement
independently re-deriving the scenario vehicle and recomputing all three metrics
(accel/range/braking) even when it only needs one -- a naive per-requirement
implementation would do 3x more physics evaluation than necessary per requirement.
"""

from dataclasses import dataclass
from typing import Callable, List

import numpy as np

from .scenario_evaluation import ScenarioResult, evaluate_under_scenario
from .uncertainty import Scenario, UncertaintyModel, nominal_scenario
from ..design.constraints import Direction
from ..physics import VehicleParams
from ..physics.constants import MPH_TO_MPS


@dataclass(frozen=True)
class MonteCarloResult:
    metric_name: str
    unit: str
    samples: np.ndarray

    @property
    def mean(self) -> float:
        return float(np.mean(self.samples))

    @property
    def std(self) -> float:
        return float(np.std(self.samples))

    def percentile(self, pct: float) -> float:
        return float(np.percentile(self.samples, pct))


def monte_carlo_evaluate(
    vehicle: VehicleParams,
    metric: Callable[[VehicleParams, Scenario], float],
    metric_name: str,
    unit: str,
    uncertainty_model: UncertaintyModel,
    n_samples: int,
    seed: int,
) -> MonteCarloResult:
    """General-purpose single-metric propagation for ad hoc exploration (e.g. a
    "deep dive" on one candidate) -- `metric` gets the original vehicle and a
    sampled Scenario directly, typically via evaluate_under_scenario. For checking
    several requirements against the same scenario batch efficiently, use
    RobustMission instead (it shares each scenario's ScenarioResult across
    requirements rather than recomputing per requirement).
    """
    rng = np.random.default_rng(seed)
    scenarios = uncertainty_model.sample_many(n_samples, rng)
    samples = np.array([metric(vehicle, s) for s in scenarios])
    return MonteCarloResult(metric_name=metric_name, unit=unit, samples=samples)


@dataclass(frozen=True)
class RobustRequirementResult:
    name: str
    direction: Direction
    threshold: float
    unit: str
    reliability_target: float
    fraction_satisfied: float
    satisfied: bool  # fraction_satisfied >= reliability_target
    nominal_value: float  # value at the single nominal_scenario(), for comparison
    worst_value: float  # value at whichever sampled scenario was closest to violating


@dataclass(frozen=True)
class RobustRequirement:
    name: str
    direction: Direction
    threshold: float
    unit: str
    metric: Callable[[ScenarioResult], float]  # extracts one number from an already-computed ScenarioResult
    reliability_target: float = 0.95

    def evaluate(self, scenario_results: List[ScenarioResult], nominal_result: ScenarioResult) -> RobustRequirementResult:
        values = np.array([self.metric(sr) for sr in scenario_results])
        if self.direction is Direction.AT_MOST:
            passed = values <= self.threshold
            worst_value = float(values.max())
        else:
            passed = values >= self.threshold
            worst_value = float(values.min())
        fraction_satisfied = float(np.mean(passed))
        return RobustRequirementResult(
            name=self.name,
            direction=self.direction,
            threshold=self.threshold,
            unit=self.unit,
            reliability_target=self.reliability_target,
            fraction_satisfied=fraction_satisfied,
            satisfied=fraction_satisfied >= self.reliability_target,
            nominal_value=self.metric(nominal_result),
            worst_value=worst_value,
        )


@dataclass(frozen=True)
class RobustMission:
    name: str
    requirements: List[RobustRequirement]
    uncertainty_model: UncertaintyModel
    highway_speed_mps: float = 65.0 * MPH_TO_MPS

    def evaluate(self, vehicle: VehicleParams, n_samples: int, seed: int) -> List[RobustRequirementResult]:
        rng = np.random.default_rng(seed)
        scenarios = self.uncertainty_model.sample_many(n_samples, rng)
        scenario_results = [evaluate_under_scenario(vehicle, s, self.highway_speed_mps) for s in scenarios]
        nominal_result = evaluate_under_scenario(vehicle, nominal_scenario(), self.highway_speed_mps)
        return [r.evaluate(scenario_results, nominal_result) for r in self.requirements]

    @staticmethod
    def is_feasible(results: List[RobustRequirementResult]) -> bool:
        return all(r.satisfied for r in results)
