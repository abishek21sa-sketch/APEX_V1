"""Phase 3 of the APEX platform: the engineering design-space representation and
constraint system that sits between the Phase 1/2 physics kernel and Phase 4's
optimizer.

    variables.py    -- ContinuousVariable/DiscreteVariable/DesignSpace: the space
    components.py   -- named discrete-choice presets (motor architecture, battery
                        chemistry, tire) bundling the physical properties a real
                        engineering decision carries together
    candidate.py     -- DesignCandidate (one point in the space) + build_vehicle():
                        the mass/cost buildup turning it into a VehicleParams
    constraints.py   -- Requirement/Mission: engineering requirements evaluated
                        against a built candidate via the physics kernel

Nothing here performs optimization (that's Phase 4, CasADi/pymoo/OR-Tools per the
roadmap) -- this module only defines what a candidate *is* and whether it's
feasible, which is exactly what an optimizer needs handed to it.
"""

from .variables import ContinuousVariable, DesignSpace, DesignVariable, DiscreteVariable
from .components import BATTERY_CHEMISTRIES, MOTOR_ARCHITECTURES, TIRE_CHOICES, BatteryChemistry, MotorArchitecture, TireChoice
from .candidate import BuildupReport, DesignCandidate, PlatformContext, build_vehicle, default_design_space, random_candidate
from .constraints import (
    Direction,
    Mission,
    Requirement,
    RequirementResult,
    example_crossover_mission,
    max_acceleration_time_s,
    max_braking_distance_m,
    max_manufacturing_cost_usd,
    max_mass_kg,
    min_gradeability_pct,
    min_highway_range_mi,
)

__all__ = [
    "ContinuousVariable",
    "DesignSpace",
    "DesignVariable",
    "DiscreteVariable",
    "BATTERY_CHEMISTRIES",
    "MOTOR_ARCHITECTURES",
    "TIRE_CHOICES",
    "BatteryChemistry",
    "MotorArchitecture",
    "TireChoice",
    "BuildupReport",
    "DesignCandidate",
    "PlatformContext",
    "build_vehicle",
    "default_design_space",
    "random_candidate",
    "Direction",
    "Mission",
    "Requirement",
    "RequirementResult",
    "example_crossover_mission",
    "max_acceleration_time_s",
    "max_braking_distance_m",
    "max_manufacturing_cost_usd",
    "max_mass_kg",
    "min_gradeability_pct",
    "min_highway_range_mi",
]
