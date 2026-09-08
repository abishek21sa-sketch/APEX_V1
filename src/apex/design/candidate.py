"""A DesignCandidate is one point in the design space (variables.py); build_vehicle()
turns it into a fully consistent VehicleParams via mass/cost buildup, operationalizing
the platform's central MDO claim -- battery <-> mass <-> range <-> motor <-> cost are
coupled, so a candidate's mass isn't a free choice, it's a consequence of the battery
and motor sizing decisions actually made.

DesignCandidate deliberately does NOT include mass, cost, or motor_peak_torque_nm --
those are derived here, not chosen, exactly like a real design wouldn't let an engineer
independently pick a vehicle's mass and battery size as unrelated numbers.
"""

from dataclasses import dataclass, asdict

import numpy as np

from .components import BATTERY_CHEMISTRIES, MOTOR_ARCHITECTURES, TIRE_CHOICES
from .variables import ContinuousVariable, DesignSpace, DiscreteVariable
from ..physics import VehicleParams


@dataclass(frozen=True)
class DesignCandidate:
    battery_capacity_kwh: float
    motor_power_kw: float
    gear_ratio: float
    drag_coefficient: float
    frontal_area_m2: float
    motor_architecture: str
    battery_chemistry: str
    num_motors: str  # "1" or "2" -- kept as str so it's a plain DiscreteVariable, not a special case
    tire_choice: str

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PlatformContext:
    """Fixed, non-optimized inputs needed to complete a VehicleParams: the parts of
    the vehicle Phase 3 doesn't treat as a free design variable (body-in-white,
    interior, brakes, non-powertrain manufacturing cost). One representative
    "compact crossover" platform -- an order-of-magnitude planning figure, not
    sourced from any real vehicle's bill of materials.
    """

    name: str = "compact_crossover_glider"
    glider_mass_kg: float = 950.0
    glider_manufacturing_cost: float = 19000.0
    battery_nominal_voltage_v: float = 400.0


@dataclass(frozen=True)
class BuildupReport:
    battery_mass_kg: float
    motor_mass_kg: float
    glider_mass_kg: float
    tire_mass_delta_kg: float
    total_mass_kg: float
    battery_cost: float
    motor_cost: float
    glider_cost: float
    tire_cost_delta: float
    total_manufacturing_cost: float


def build_vehicle(candidate: DesignCandidate, context: PlatformContext = PlatformContext()) -> tuple[VehicleParams, BuildupReport]:
    architecture = MOTOR_ARCHITECTURES[candidate.motor_architecture]
    chemistry = BATTERY_CHEMISTRIES[candidate.battery_chemistry]
    tire = TIRE_CHOICES[candidate.tire_choice]
    num_motors = int(candidate.num_motors)

    battery_mass_kg = candidate.battery_capacity_kwh * chemistry.specific_mass_kg_per_kwh
    battery_cost = candidate.battery_capacity_kwh * chemistry.cost_per_kwh

    motor_mass_kg = candidate.motor_power_kw / architecture.specific_power_kw_per_kg
    motor_cost = candidate.motor_power_kw * architecture.cost_per_kw
    # A second motor adds gearbox/inverter/mounting overhead beyond what one unit of
    # the same *combined* power needs -- num_motors doesn't change motor_power_kw
    # (still the vehicle's total combined rating), just this fixed per-extra-unit
    # penalty, not a full second bill of materials.
    motor_mass_kg += 12.0 * (num_motors - 1)
    motor_cost += 350.0 * (num_motors - 1)

    total_mass_kg = context.glider_mass_kg + battery_mass_kg + motor_mass_kg + tire.mass_delta_kg
    total_manufacturing_cost = context.glider_manufacturing_cost + battery_cost + motor_cost + tire.cost_delta

    base_speed_rad_s = architecture.base_speed_rpm * 2.0 * np.pi / 60.0
    motor_peak_torque_nm = candidate.motor_power_kw * 1000.0 / base_speed_rad_s

    vehicle = VehicleParams(
        name=(
            f"candidate({candidate.battery_capacity_kwh:.0f}kWh/{candidate.motor_power_kw:.0f}kW/"
            f"{architecture.name}/{chemistry.name}/{tire.name}/{num_motors}m)"
        ),
        mass_kg=total_mass_kg,
        drag_coefficient=candidate.drag_coefficient,
        frontal_area_m2=candidate.frontal_area_m2,
        rolling_resistance_coeff=tire.rolling_resistance_coeff,
        wheel_radius_m=tire.wheel_radius_m,
        tire_friction_coeff=tire.tire_friction_coeff,
        motor_power_kw=candidate.motor_power_kw,
        motor_peak_torque_nm=motor_peak_torque_nm,
        gear_ratio=candidate.gear_ratio,
        drivetrain_efficiency=architecture.drivetrain_efficiency,
        regen_efficiency=architecture.regen_efficiency,
        max_motor_rpm=architecture.max_motor_rpm,
        battery_usable_kwh=candidate.battery_capacity_kwh,
        battery_nominal_voltage_v=context.battery_nominal_voltage_v,
        battery_max_c_rate_discharge=chemistry.max_c_rate_discharge,
        battery_max_c_rate_charge=chemistry.max_c_rate_charge,
    )

    report = BuildupReport(
        battery_mass_kg=battery_mass_kg,
        motor_mass_kg=motor_mass_kg,
        glider_mass_kg=context.glider_mass_kg,
        tire_mass_delta_kg=tire.mass_delta_kg,
        total_mass_kg=total_mass_kg,
        battery_cost=battery_cost,
        motor_cost=motor_cost,
        glider_cost=context.glider_manufacturing_cost,
        tire_cost_delta=tire.cost_delta,
        total_manufacturing_cost=total_manufacturing_cost,
    )
    return vehicle, report


def default_design_space() -> DesignSpace:
    return DesignSpace(
        variables=[
            ContinuousVariable("battery_capacity_kwh", 30.0, 120.0, unit="kWh"),
            ContinuousVariable("motor_power_kw", 60.0, 400.0, unit="kW"),
            ContinuousVariable("gear_ratio", 5.0, 12.0, unit=":1"),
            ContinuousVariable("drag_coefficient", 0.20, 0.38, unit="Cd"),
            ContinuousVariable("frontal_area_m2", 2.0, 2.8, unit="m^2"),
            DiscreteVariable("motor_architecture", list(MOTOR_ARCHITECTURES.keys())),
            DiscreteVariable("battery_chemistry", list(BATTERY_CHEMISTRIES.keys())),
            DiscreteVariable("num_motors", ["1", "2"]),
            DiscreteVariable("tire_choice", list(TIRE_CHOICES.keys())),
        ]
    )


def random_candidate(design_space: DesignSpace, rng: np.random.Generator) -> DesignCandidate:
    values = {}
    for v in design_space.continuous:
        values[v.name] = float(rng.uniform(v.lower, v.upper))
    for v in design_space.discrete:
        values[v.name] = str(rng.choice(list(v.choices)))
    return DesignCandidate(**values)
