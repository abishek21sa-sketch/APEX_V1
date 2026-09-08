"""Turns a Scenario into a scenario-adjusted VehicleParams + BatteryState, so every
existing Phase 1-4 evaluator (zero_to_sixty_s, constant_speed_range_km,
braking_distance_m, Requirement, Objective) works completely unchanged on it --
robustness is handled entirely by *what vehicle gets passed in*, not by rewriting
the physics kernel or the constraint/objective machinery.

Payload adds mass. Tire wear raises rolling resistance and -- via a documented,
not independently measured, linear linkage -- reduces peak grip. Ambient
temperature and battery state-of-health feed battery.py's existing thermal- and
SOH-derating (built in Phase 2, unused by Phase 1-4's nominal evaluation) to cap
motor_power_kw at whatever the pack can actually deliver, and scale down usable
energy for range. This is why cold weather and an aged pack show up as reduced
acceleration and range here even though longitudinal.py's force-availability
model never changed -- the battery, not the motor, becomes the binding limit.
"""

import dataclasses
from typing import Tuple

from .uncertainty import Scenario
from .. import physics
from ..physics import BatteryState, VehicleParams
from ..physics.constants import MPH_TO_MPS


def apply_scenario(vehicle: VehicleParams, scenario: Scenario) -> Tuple[VehicleParams, BatteryState]:
    battery_state = BatteryState(
        soc=vehicle.battery_max_soc,
        temperature_c=scenario.ambient_temp_c,
        state_of_health=scenario.battery_soh,
    )

    battery_limited_current_a = physics.max_discharge_current_a(vehicle, battery_state)
    battery_limited_power_kw = battery_limited_current_a * physics.open_circuit_voltage(vehicle, battery_state.soc) / 1000.0

    scenario_vehicle = dataclasses.replace(
        vehicle,
        mass_kg=vehicle.mass_kg + scenario.payload_kg,
        rolling_resistance_coeff=vehicle.rolling_resistance_coeff * scenario.tire_wear_factor,
        tire_friction_coeff=vehicle.tire_friction_coeff * (2.0 - scenario.tire_wear_factor),
        motor_power_kw=min(vehicle.motor_power_kw, battery_limited_power_kw),
        battery_usable_kwh=vehicle.battery_usable_kwh * scenario.battery_soh,
    )
    return scenario_vehicle, battery_state


@dataclasses.dataclass(frozen=True)
class ScenarioResult:
    scenario: Scenario
    zero_to_sixty_s: float
    range_mi: float
    braking_distance_m: float


def evaluate_under_scenario(vehicle: VehicleParams, scenario: Scenario, highway_speed_mps: float) -> ScenarioResult:
    scenario_vehicle, _ = apply_scenario(vehicle, scenario)
    return ScenarioResult(
        scenario=scenario,
        zero_to_sixty_s=physics.zero_to_sixty_s(scenario_vehicle, grade=scenario.road_grade),
        # Range is inherently a flat/level-terrain metric here (a nonzero constant
        # grade forever isn't a meaningful "range" -- see the module docstring in
        # physics/energy.py), so road_grade doesn't apply to it.
        range_mi=physics.constant_speed_range_km(scenario_vehicle, highway_speed_mps) * 0.621371,
        braking_distance_m=physics.braking_distance_m(scenario_vehicle, 60.0 * MPH_TO_MPS),
    )
