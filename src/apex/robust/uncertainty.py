"""Uncertain operating parameters a real vehicle sees across its service life,
per the platform proposal's own list: "payload, temperature, road grade, wind,
tire resistance, battery degradation, driver behavior." Wind and driver behavior
aren't modeled (no mechanism in this kernel to apply them distinctly from the
others) -- payload, ambient temperature, road grade, tire wear, and battery
state-of-health are.

All five are independent uniform distributions -- a simple, honest starting point
for Monte Carlo propagation, not a claim that real-world variation is uniformly
distributed (a triangular or normal distribution centered on a "typical" value
would be more realistic; uniform is the conservative choice when no distribution
shape has actually been measured).
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Scenario:
    """One sampled realization of the uncertain operating parameters."""

    payload_kg: float
    ambient_temp_c: float
    road_grade: float
    tire_wear_factor: float  # 1.0 = new tires, >1.0 = worn (higher rolling resistance, less grip)
    battery_soh: float  # 1.0 = new pack, <1.0 = degraded (less usable capacity, less current capability)


@dataclass(frozen=True)
class UncertaintyModel:
    payload_kg_range: tuple = (0.0, 400.0)  # empty car to ~4-5 occupants + cargo
    ambient_temp_c_range: tuple = (-20.0, 40.0)  # cold winter to hot summer
    road_grade_range: tuple = (-0.02, 0.06)  # everyday grade variation, not mountain passes
    tire_wear_factor_range: tuple = (1.0, 1.25)
    battery_soh_range: tuple = (0.85, 1.0)  # expected range across the design's service life

    def sample(self, rng: np.random.Generator) -> Scenario:
        return Scenario(
            payload_kg=float(rng.uniform(*self.payload_kg_range)),
            ambient_temp_c=float(rng.uniform(*self.ambient_temp_c_range)),
            road_grade=float(rng.uniform(*self.road_grade_range)),
            tire_wear_factor=float(rng.uniform(*self.tire_wear_factor_range)),
            battery_soh=float(rng.uniform(*self.battery_soh_range)),
        )

    def sample_many(self, n: int, rng: np.random.Generator) -> list:
        return [self.sample(rng) for _ in range(n)]


def nominal_scenario() -> Scenario:
    """The single operating point Phases 1-4 implicitly evaluate at: no payload,
    room temperature, flat road, new tires, a fresh pack. Useful for comparing a
    candidate's nominal figures (Phase 4's) against its robust ones (Phase 5's).
    """
    return Scenario(payload_kg=0.0, ambient_temp_c=25.0, road_grade=0.0, tire_wear_factor=1.0, battery_soh=1.0)
