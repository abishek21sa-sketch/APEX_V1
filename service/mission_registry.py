"""Maps a JSON-friendly mission spec (a list of {kind, threshold} requirement
descriptions) onto the real design.constraints.Requirement constructors -- the
HTTP boundary's translation layer, since a Mission's Requirement objects (Python
closures wrapping physics-kernel calls) aren't JSON-serializable and have no
business being reconstructed ad hoc at every call site that needs one.
"""

from typing import Callable, Dict, List

from apex.design import (
    Mission,
    Requirement,
    max_acceleration_time_s,
    max_braking_distance_m,
    max_manufacturing_cost_usd,
    max_mass_kg,
    min_gradeability_pct,
    min_highway_range_mi,
)
from apex.robust import (
    RobustMission,
    RobustRequirement,
    UncertaintyModel,
    robust_max_acceleration_time_s,
    robust_max_braking_distance_m,
    robust_min_highway_range_mi,
)

_REQUIREMENT_KINDS: Dict[str, Callable[[float], Requirement]] = {
    "max_acceleration_time_s": max_acceleration_time_s,
    "min_highway_range_mi": min_highway_range_mi,
    "max_mass_kg": max_mass_kg,
    "min_gradeability_pct": min_gradeability_pct,
    "max_braking_distance_m": max_braking_distance_m,
    "max_manufacturing_cost_usd": max_manufacturing_cost_usd,
}

REQUIREMENT_KINDS = sorted(_REQUIREMENT_KINDS)

# Cost isn't here: manufacturing cost is a static property of the design, not
# something that varies with the operating scenario -- see robust/requirements.py.
_ROBUST_REQUIREMENT_KINDS: Dict[str, Callable[[float], RobustRequirement]] = {
    "max_acceleration_time_s": robust_max_acceleration_time_s,
    "min_highway_range_mi": robust_min_highway_range_mi,
    "max_braking_distance_m": robust_max_braking_distance_m,
}

ROBUST_REQUIREMENT_KINDS = sorted(_ROBUST_REQUIREMENT_KINDS)


def build_mission(name: str, requirement_specs: List[dict]) -> Mission:
    requirements = []
    for spec in requirement_specs:
        kind = spec["kind"]
        if kind not in _REQUIREMENT_KINDS:
            raise ValueError(f"unknown requirement kind {kind!r}; expected one of {REQUIREMENT_KINDS}")
        requirements.append(_REQUIREMENT_KINDS[kind](spec["threshold"]))
    return Mission(name=name, requirements=requirements)


def build_robust_mission(name: str, requirement_specs: List[dict]) -> RobustMission:
    requirements = []
    for spec in requirement_specs:
        kind = spec["kind"]
        if kind not in _ROBUST_REQUIREMENT_KINDS:
            raise ValueError(
                f"unknown or unsupported robust requirement kind {kind!r}; expected one of {ROBUST_REQUIREMENT_KINDS}"
            )
        requirements.append(_ROBUST_REQUIREMENT_KINDS[kind](spec["threshold"]))
    return RobustMission(name=name, requirements=requirements, uncertainty_model=UncertaintyModel())
