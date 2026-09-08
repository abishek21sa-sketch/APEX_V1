"""Standard RobustRequirement constructors, mirroring design.constraints's plain
(nominal-only) requirement constructors but each extracting its metric from a
shared, already-computed ScenarioResult (see robust.py) rather than recomputing
physics independently. Cost isn't offered here: manufacturing cost is a static
property of the *design* (battery capacity, rated motor power), not something
that varies with the operating scenario, so a "robust cost" requirement wouldn't
mean anything different from the plain one in design.constraints.
"""

from .robust import RobustMission, RobustRequirement
from .uncertainty import UncertaintyModel
from ..design.constraints import Direction


def robust_max_acceleration_time_s(threshold_s: float, reliability_target: float = 0.95) -> RobustRequirement:
    return RobustRequirement(
        name="0-60 mph time",
        direction=Direction.AT_MOST,
        threshold=threshold_s,
        unit="s",
        reliability_target=reliability_target,
        metric=lambda sr: sr.zero_to_sixty_s,
    )


def robust_min_highway_range_mi(threshold_mi: float, reliability_target: float = 0.95) -> RobustRequirement:
    return RobustRequirement(
        name="highway range",
        direction=Direction.AT_LEAST,
        threshold=threshold_mi,
        unit="mi",
        reliability_target=reliability_target,
        metric=lambda sr: sr.range_mi,
    )


def robust_max_braking_distance_m(threshold_m: float, reliability_target: float = 0.95) -> RobustRequirement:
    return RobustRequirement(
        name="60-0mph braking distance",
        direction=Direction.AT_MOST,
        threshold=threshold_m,
        unit="m",
        reliability_target=reliability_target,
        metric=lambda sr: sr.braking_distance_m,
    )


def robust_crossover_mission(uncertainty_model: UncertaintyModel = UncertaintyModel()) -> RobustMission:
    """The robust counterpart of design.constraints.example_crossover_mission(),
    minus the (scenario-invariant) cost requirement -- see this module's docstring.
    """
    return RobustMission(
        name="sub-$42k electric crossover, >=310mi range, sub-6s 0-60 (robust)",
        requirements=[
            robust_max_acceleration_time_s(6.0),
            robust_min_highway_range_mi(310.0),
        ],
        uncertainty_model=uncertainty_model,
    )
