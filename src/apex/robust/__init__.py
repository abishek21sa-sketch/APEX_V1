"""Phase 5 of the APEX platform: Monte Carlo uncertainty propagation and a
chance-constrained relaxation of robust design optimization, on top of the
Phase 1-4 kernel/design-space/optimizer.

    uncertainty.py         -- Scenario/UncertaintyModel: what varies (payload,
                               ambient temperature, road grade, tire wear,
                               battery state-of-health) and how it's sampled
    scenario_evaluation.py -- apply_scenario(): turns a Scenario into a
                               scenario-adjusted VehicleParams + BatteryState, so
                               every existing Phase 1-4 evaluator works unchanged
    robust.py               -- MonteCarloResult, RobustRequirement/RobustMission:
                               chance-constrained feasibility ("satisfied in at
                               least `reliability_target` of sampled scenarios")
    requirements.py          -- standard RobustRequirement constructors mirroring
                               design.constraints's plain ones

A candidate that looks feasible under design.constraints.Mission (Phase 3/4's
single nominal operating point) can still fail RobustMission -- that gap is
exactly what this phase is for: Phase 4 optimizes over what Phase 3 considers
"the design"; Phase 5 checks whether that design actually holds up once payload,
weather, tire wear, and battery aging are allowed to vary.
"""

from .uncertainty import Scenario, UncertaintyModel, nominal_scenario
from .scenario_evaluation import ScenarioResult, apply_scenario, evaluate_under_scenario
from .robust import MonteCarloResult, RobustMission, RobustRequirement, RobustRequirementResult, monte_carlo_evaluate
from .requirements import (
    robust_crossover_mission,
    robust_max_acceleration_time_s,
    robust_max_braking_distance_m,
    robust_min_highway_range_mi,
)

__all__ = [
    "Scenario",
    "UncertaintyModel",
    "nominal_scenario",
    "ScenarioResult",
    "apply_scenario",
    "evaluate_under_scenario",
    "MonteCarloResult",
    "RobustMission",
    "RobustRequirement",
    "RobustRequirementResult",
    "monte_carlo_evaluate",
    "robust_crossover_mission",
    "robust_max_acceleration_time_s",
    "robust_max_braking_distance_m",
    "robust_min_highway_range_mi",
]

from .design_selection import RobustDesignScore, evaluate_shortlist, select_robust_design
from .release_assurance import build_design_release_certificate, verify_design_release_certificate
