"""Longitudinal vehicle dynamics: the road-load equation and tractive-force limits.

    F_road = 1/2 * rho * Cd * Af * v^2   (aero drag)
           + Crr * m * g * cos(theta)    (rolling resistance)
           + m * g * sin(theta)          (grade)

    P_wheel = F_road * v   (plus the inertial m*a term when accelerating)

Everything downstream (performance envelope, energy integration) is built on
these two equations plus a force-availability model for the motor/tire pair.
"""

import numpy as np

from .constants import GRAVITY_MPS2, AIR_DENSITY_KG_M3
from .params import VehicleParams


def aero_drag_force(vehicle: VehicleParams, speed_mps: float) -> float:
    return 0.5 * AIR_DENSITY_KG_M3 * vehicle.drag_coefficient * vehicle.frontal_area_m2 * speed_mps**2


def rolling_resistance_force(vehicle: VehicleParams, speed_mps: float, grade: float = 0.0) -> float:
    if speed_mps <= 0:
        return 0.0
    theta = np.arctan(grade)
    return vehicle.rolling_resistance_coeff * vehicle.mass_kg * GRAVITY_MPS2 * np.cos(theta)


def grade_force(vehicle: VehicleParams, grade: float = 0.0) -> float:
    """Component of gravity along the road surface. grade is rise/run (e.g. 0.06 = 6%)."""
    theta = np.arctan(grade)
    return vehicle.mass_kg * GRAVITY_MPS2 * np.sin(theta)


def road_load_force(vehicle: VehicleParams, speed_mps: float, grade: float = 0.0) -> float:
    """Steady-state force required to hold speed_mps on the given grade.
    Excludes the m*a inertial term — add it separately for accelerating cases.
    """
    return (
        aero_drag_force(vehicle, speed_mps)
        + rolling_resistance_force(vehicle, speed_mps, grade)
        + grade_force(vehicle, grade)
    )


def wheel_power_required(vehicle: VehicleParams, speed_mps: float, grade: float = 0.0, accel_mps2: float = 0.0) -> float:
    f_total = road_load_force(vehicle, speed_mps, grade) + vehicle.mass_kg * accel_mps2
    return f_total * speed_mps


def max_traction_force(vehicle: VehicleParams) -> float:
    """Tire-road adhesion ceiling: mu * m * g. Assumes full mass is available for
    traction (i.e. all-wheel drive) — a real front/rear weight-transfer model is
    part of the vehicle-dynamics layer (bicycle model), not this longitudinal kernel.
    """
    return vehicle.tire_friction_coeff * vehicle.mass_kg * GRAVITY_MPS2


def max_motor_speed_mps(vehicle: VehicleParams) -> float:
    """Road speed at which the motor hits its RPM redline, given the fixed gear_ratio.
    With no multi-speed gearbox to shift down, this is the real top-speed limiter on
    most single-speed-reduction EVs.
    """
    motor_omega_max = vehicle.max_motor_rpm * 2.0 * np.pi / 60.0
    wheel_omega_max = motor_omega_max / vehicle.gear_ratio
    return wheel_omega_max * vehicle.wheel_radius_m


def motor_force_limit(vehicle: VehicleParams, speed_mps: float) -> float:
    """Wheel force the motor/gearbox can deliver, before the tire-traction ceiling.

    Constant-torque region up to a base speed (torque-limited), then constant-power
    region beyond it (power-limited, force ~ 1/v) — the classic EV force-speed curve —
    dropping to zero once the motor's RPM redline is reached (see max_motor_speed_mps).
    """
    if speed_mps > max_motor_speed_mps(vehicle):
        return 0.0
    f_torque_limited = (
        vehicle.motor_peak_torque_nm * vehicle.gear_ratio * vehicle.drivetrain_efficiency / vehicle.wheel_radius_m
    )
    if speed_mps <= 1e-3:
        return f_torque_limited
    f_power_limited = vehicle.motor_power_kw * 1000.0 * vehicle.drivetrain_efficiency / speed_mps
    return min(f_torque_limited, f_power_limited)


def available_wheel_force(vehicle: VehicleParams, speed_mps: float) -> float:
    """Net force the drivetrain can actually put to the road at this speed."""
    return min(motor_force_limit(vehicle, speed_mps), max_traction_force(vehicle))
