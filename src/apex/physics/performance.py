"""Vehicle performance envelope: acceleration, top speed, gradeability, braking.

Each of these is the same idea applied differently: find where net longitudinal
force (available_wheel_force - road_load_force) crosses zero, or integrate the
resulting acceleration forward/backward in time.
"""

from typing import Tuple

import numpy as np
from scipy.optimize import brentq

from .constants import GRAVITY_MPS2, MPH_TO_MPS
from .longitudinal import aero_drag_force, available_wheel_force, max_traction_force, road_load_force
from .params import VehicleParams


def simulate_acceleration(
    vehicle: VehicleParams,
    target_speed_mps: float,
    grade: float = 0.0,
    dt: float = 0.01,
    max_time_s: float = 60.0,
) -> Tuple[float, Tuple[np.ndarray, np.ndarray]]:
    """Integrate v(t) forward from a standing start under available tractive force.

    Returns (time_to_reach_target_s, (t_array, v_array)); time is `inf` if the
    target speed is never reached within max_time_s (e.g. it exceeds top speed).
    """
    effective_mass = vehicle.mass_kg * vehicle.rotational_inertia_factor
    n_max = int(max_time_s / dt)
    t = np.zeros(n_max + 1)
    v = np.zeros(n_max + 1)

    for i in range(n_max):
        f_net = available_wheel_force(vehicle, v[i]) - road_load_force(vehicle, v[i], grade)
        a = f_net / effective_mass
        v[i + 1] = max(0.0, v[i] + a * dt)
        t[i + 1] = t[i] + dt
        if v[i + 1] >= target_speed_mps:
            frac = (target_speed_mps - v[i]) / (v[i + 1] - v[i]) if v[i + 1] > v[i] else 0.0
            return t[i] + frac * dt, (t[: i + 2], v[: i + 2])

    return float("inf"), (t, v)


def zero_to_sixty_s(vehicle: VehicleParams, grade: float = 0.0) -> float:
    t, _ = simulate_acceleration(vehicle, 60.0 * MPH_TO_MPS, grade=grade)
    return t


def top_speed_mps(vehicle: VehicleParams, grade: float = 0.0, search_bounds: Tuple[float, float] = (1.0, 150.0)) -> float:
    """Speed at which available_wheel_force(v) == road_load_force(v, grade)."""

    def net_force(v: float) -> float:
        return available_wheel_force(vehicle, v) - road_load_force(vehicle, v, grade)

    lo, hi = search_bounds
    if net_force(lo) < 0:
        return 0.0  # can't even sustain the low end of the search range on this grade
    if net_force(hi) > 0:
        return hi  # power isn't the limiting factor within search_bounds; widen bounds to resolve
    return brentq(net_force, lo, hi)


def max_gradeability(vehicle: VehicleParams, speed_mps: float, search_bounds: Tuple[float, float] = (0.0, 1.0)) -> float:
    """Maximum sustainable grade (rise/run) the vehicle can hold at speed_mps."""

    def net_force(grade: float) -> float:
        return available_wheel_force(vehicle, speed_mps) - road_load_force(vehicle, speed_mps, grade)

    lo, hi = search_bounds
    if net_force(hi) >= 0:
        return hi  # grade capability exceeds search_bounds; widen bounds to resolve
    if net_force(lo) < 0:
        return 0.0  # can't hold even zero grade at this speed
    return brentq(net_force, lo, hi)


def braking_distance_m(vehicle: VehicleParams, initial_speed_mps: float, dt: float = 0.01, max_time_s: float = 30.0) -> float:
    """Distance to stop under max tire braking force, with aero drag assisting.
    Does not include driver reaction distance.
    """
    v = initial_speed_mps
    d = 0.0
    t = 0.0
    while v > 0 and t < max_time_s:
        f_brake = max_traction_force(vehicle) + aero_drag_force(vehicle, v)
        a = -f_brake / vehicle.mass_kg
        v_next = max(0.0, v + a * dt)
        d += (v + v_next) / 2 * dt
        v = v_next
        t += dt
    return d
