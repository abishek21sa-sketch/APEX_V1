"""Engineering requirements evaluated against a built candidate: the constraint
side of "given performance, range, ... requirements, what should an engineer
build?" Each Requirement wraps a physics-kernel call (0-60 time, range,
gradeability, braking distance, mass, manufacturing cost) with a direction and
threshold; a Mission is a named bundle of requirements checked together.

Explicitly NOT modeled yet, so not offered as constructors here: passenger/cargo
volume (no packaging model), lateral stability (needs the bicycle-model/lateral-
dynamics layer, not built), component reliability (needs the probabilistic/RBDO
phase), sustainability targets (needs an LCA/embodied-carbon model). Listing
what's missing rather than silently pretending full coverage matches how Phase
1/2's simplifications are documented.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, List

from .candidate import BuildupReport
from ..physics import VehicleParams, braking_distance_m, constant_speed_range_km, max_gradeability, zero_to_sixty_s
from ..physics.constants import MPH_TO_MPS


class Direction(Enum):
    AT_MOST = "at_most"
    AT_LEAST = "at_least"


@dataclass(frozen=True)
class RequirementResult:
    name: str
    value: float
    threshold: float
    unit: str
    direction: Direction
    satisfied: bool
    margin: float  # positive = slack, negative = amount by which it's violated


@dataclass(frozen=True)
class Requirement:
    name: str
    direction: Direction
    threshold: float
    unit: str
    evaluator: Callable[[VehicleParams, BuildupReport], float]

    def evaluate(self, vehicle: VehicleParams, report: BuildupReport) -> RequirementResult:
        value = self.evaluator(vehicle, report)
        if self.direction is Direction.AT_MOST:
            satisfied = value <= self.threshold
            margin = self.threshold - value
        else:
            satisfied = value >= self.threshold
            margin = value - self.threshold
        return RequirementResult(
            name=self.name,
            value=value,
            threshold=self.threshold,
            unit=self.unit,
            direction=self.direction,
            satisfied=satisfied,
            margin=margin,
        )


@dataclass(frozen=True)
class Mission:
    """A named bundle of requirements -- e.g. the platform proposal's own worked
    example: "a sub-$42k electric crossover capable of at least 310 miles of range
    while preserving 0-60 under six seconds."
    """

    name: str
    requirements: List[Requirement]

    def evaluate(self, vehicle: VehicleParams, report: BuildupReport) -> List[RequirementResult]:
        return [r.evaluate(vehicle, report) for r in self.requirements]

    @staticmethod
    def is_feasible(results: List[RequirementResult]) -> bool:
        return all(r.satisfied for r in results)


def max_acceleration_time_s(threshold_s: float) -> Requirement:
    return Requirement(
        name="0-60 mph time",
        direction=Direction.AT_MOST,
        threshold=threshold_s,
        unit="s",
        evaluator=lambda v, r: zero_to_sixty_s(v),
    )


def min_highway_range_mi(threshold_mi: float, speed_mps: float = 65.0 * MPH_TO_MPS) -> Requirement:
    return Requirement(
        name=f"range @ {speed_mps / MPH_TO_MPS:.0f}mph",
        direction=Direction.AT_LEAST,
        threshold=threshold_mi,
        unit="mi",
        evaluator=lambda v, r: constant_speed_range_km(v, speed_mps) * 0.621371,
    )


def max_mass_kg(threshold_kg: float) -> Requirement:
    return Requirement(
        name="curb mass",
        direction=Direction.AT_MOST,
        threshold=threshold_kg,
        unit="kg",
        evaluator=lambda v, r: v.mass_kg,
    )


def min_gradeability_pct(threshold_pct: float, speed_mps: float = 20.0) -> Requirement:
    return Requirement(
        name=f"gradeability @ {speed_mps:.0f}m/s",
        direction=Direction.AT_LEAST,
        threshold=threshold_pct,
        unit="%",
        evaluator=lambda v, r: max_gradeability(v, speed_mps) * 100.0,
    )


def max_braking_distance_m(threshold_m: float, from_speed_mps: float = 60.0 * MPH_TO_MPS) -> Requirement:
    return Requirement(
        name=f"{from_speed_mps / MPH_TO_MPS:.0f}-0mph braking distance",
        direction=Direction.AT_MOST,
        threshold=threshold_m,
        unit="m",
        evaluator=lambda v, r: braking_distance_m(v, from_speed_mps),
    )


def max_manufacturing_cost_usd(threshold_usd: float) -> Requirement:
    return Requirement(
        name="manufacturing cost",
        direction=Direction.AT_MOST,
        threshold=threshold_usd,
        unit="USD",
        evaluator=lambda v, r: r.total_manufacturing_cost,
    )


def example_crossover_mission(msrp_markup_factor: float = 1.4) -> Mission:
    """The proposal's own worked example: "Design a sub-$42k electric crossover
    capable of at least 310 miles of range while preserving 0-60 under six seconds."

    $42k reads as a target sale price (MSRP), not manufacturing cost, but this
    platform has no MSRP/pricing-structure model -- only the mass/cost buildup's
    manufacturing cost. msrp_markup_factor is a documented, representative
    cost-to-MSRP ratio (~1.3-1.8x is typical for automotive) used to convert the
    $42k target into a manufacturing-cost cap; it's an approximation flagged here,
    not a modeled pricing structure.
    """
    return Mission(
        name="sub-$42k electric crossover, >=310mi range, sub-6s 0-60",
        requirements=[
            max_acceleration_time_s(6.0),
            min_highway_range_mi(310.0),
            max_manufacturing_cost_usd(42000.0 / msrp_markup_factor),
        ],
    )
