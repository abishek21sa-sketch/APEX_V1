"""Optimization objectives: the same wrap-a-physics-call pattern as
design.constraints.Requirement, but for quantities to minimize/maximize rather
than to gate feasibility. Deliberately limited to what Phases 1-3 can actually
compute -- cost, mass, 0-60 time, and range -- not the platform proposal's full
[Cost, Energy, Mass, ThermalRisk] / [Range, Performance, SafetyMargin, RideQuality]
list. ThermalRisk, SafetyMargin, and RideQuality all need models this repository
doesn't have yet (a standalone thermal-risk metric beyond Phase 2's current-limit
derating, a lateral/stability model, a suspension/ride model) -- adding objective
functions for them now would mean inventing numbers to optimize against, which is
exactly the kind of fabricated composite metric this platform is meant to avoid.
"""

from dataclasses import dataclass
from typing import Callable, List

from ..design.candidate import BuildupReport
from ..physics import VehicleParams, constant_speed_range_km, zero_to_sixty_s
from ..physics.constants import MPH_TO_MPS


@dataclass(frozen=True)
class Objective:
    name: str
    unit: str
    evaluator: Callable[[VehicleParams, BuildupReport], float]
    minimize: bool = True  # False = maximize; internally negated for pymoo's minimize-only convention

    def raw_value(self, vehicle: VehicleParams, report: BuildupReport) -> float:
        """The quantity in its natural units and direction -- what a human reads."""
        return self.evaluator(vehicle, report)

    def signed_value(self, vehicle: VehicleParams, report: BuildupReport) -> float:
        """What pymoo actually minimizes: raw_value, negated if this is a maximize objective."""
        value = self.raw_value(vehicle, report)
        return value if self.minimize else -value


def minimize_manufacturing_cost() -> Objective:
    return Objective(name="manufacturing cost", unit="USD", evaluator=lambda v, r: r.total_manufacturing_cost, minimize=True)


def minimize_mass() -> Objective:
    return Objective(name="mass", unit="kg", evaluator=lambda v, r: v.mass_kg, minimize=True)


def minimize_zero_to_sixty() -> Objective:
    return Objective(name="0-60 mph time", unit="s", evaluator=lambda v, r: zero_to_sixty_s(v), minimize=True)


def maximize_highway_range(speed_mps: float = 65.0 * MPH_TO_MPS) -> Objective:
    return Objective(
        name=f"range @ {speed_mps / MPH_TO_MPS:.0f}mph",
        unit="mi",
        evaluator=lambda v, r: constant_speed_range_km(v, speed_mps) * 0.621371,
        minimize=False,
    )


def default_objectives() -> List[Objective]:
    """Cost and mass pull toward smaller/cheaper; 0-60 time and range pull toward
    bigger motors and bigger batteries -- four genuinely conflicting objectives,
    exactly the kind of trade space a Pareto frontier (not a single scalarized
    "best" design) is supposed to expose.
    """
    return [minimize_manufacturing_cost(), minimize_mass(), minimize_zero_to_sixty(), maximize_highway_range()]
