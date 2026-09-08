"""Trip energy consumption via numerical integration over a speed-vs-time profile:

    E = integral(P_traction(t) / eta_drive) dt  -  integral(eta_regen * P_regen(t)) dt

Positive wheel power draws from the battery through the drivetrain efficiency;
negative wheel power (deceleration) recovers energy through the regen path, capped
at the motor's power rating since the same machine does both jobs.

simulate_drive_cycle() (Phase 1) uses vehicle.drivetrain_efficiency/regen_efficiency
as flat scalars -- fast, and already validated against reference-vehicle range figures
(tests/test_validation.py). simulate_drive_cycle_with_battery() (Phase 2) replaces those
scalars with the speed/torque-aware motor.motor_efficiency() map and tracks actual
battery SOC/voltage/current through battery.py's equivalent-circuit model, including
its C-rate/thermal current limits -- more physically detailed, and needed once a use
case cares about SOC trajectory or power-delivery limits, not just net trip energy.
"""

import numpy as np

from . import battery, motor
from .battery import BatteryState
from .longitudinal import road_load_force, wheel_power_required
from .params import VehicleParams


def simulate_drive_cycle(vehicle: VehicleParams, t_s: np.ndarray, v_mps: np.ndarray) -> dict:
    t_s = np.asarray(t_s, dtype=float)
    v_mps = np.asarray(v_mps, dtype=float)
    if t_s.shape != v_mps.shape or t_s.size < 2:
        raise ValueError("t_s and v_mps must be equal-length arrays of at least 2 samples")

    accel = np.gradient(v_mps, t_s)
    f_road = np.array([road_load_force(vehicle, v) for v in v_mps])
    f_total = f_road + vehicle.mass_kg * accel
    p_wheel = f_total * v_mps  # W; positive = traction, negative = regen braking

    p_regen_limit_w = vehicle.motor_power_kw * 1000.0
    p_battery = np.where(
        p_wheel >= 0,
        p_wheel / vehicle.drivetrain_efficiency,
        np.maximum(p_wheel, -p_regen_limit_w) * vehicle.regen_efficiency,
    )

    energy_kwh = np.trapezoid(p_battery, t_s) / 3.6e6
    distance_km = np.trapezoid(v_mps, t_s) / 1000.0
    duration_s = t_s[-1] - t_s[0]

    return {
        "energy_kwh": energy_kwh,
        "distance_km": distance_km,
        "duration_s": duration_s,
        "avg_speed_kmh": distance_km / (duration_s / 3600.0) if duration_s > 0 else 0.0,
        "consumption_kwh_per_100km": (energy_kwh / distance_km * 100.0) if distance_km > 0 else float("inf"),
    }


def range_from_cycle(vehicle: VehicleParams, t_s: np.ndarray, v_mps: np.ndarray) -> float:
    """Estimated range (km): usable battery energy divided by this cycle's consumption rate."""
    result = simulate_drive_cycle(vehicle, t_s, v_mps)
    if result["energy_kwh"] <= 0:
        return float("inf")  # net-regenerative profile (e.g. all downhill) -- not a realistic range case
    return vehicle.battery_usable_kwh / result["energy_kwh"] * result["distance_km"]


def constant_speed_range_km(vehicle: VehicleParams, speed_mps: float) -> float:
    """Steady-state range at one fixed speed. Ignores accessory/HVAC load and
    real-world drive-cycle transients -- a simplified reference point, not an
    EPA-equivalent figure (EPA range uses a weighted multi-cycle test procedure).
    """
    p_wheel_w = wheel_power_required(vehicle, speed_mps)
    p_battery_kw = p_wheel_w / vehicle.drivetrain_efficiency / 1000.0
    if p_battery_kw <= 0 or speed_mps <= 0:
        return float("inf")
    hours_of_range = vehicle.battery_usable_kwh / p_battery_kw
    return hours_of_range * speed_mps * 3.6


def simulate_drive_cycle_with_battery(
    vehicle: VehicleParams,
    t_s: np.ndarray,
    v_mps: np.ndarray,
    initial_state: BatteryState = None,
    ambient_temp_c: float = 25.0,
) -> dict:
    """Time-stepped drive-cycle simulation tracking battery SOC/voltage/current via
    the equivalent-circuit model in battery.py and the speed/torque-aware efficiency
    map in motor.py, instead of simulate_drive_cycle()'s single flat-efficiency energy
    balance. At each step, desired current is clipped to the pack's C-rate- and
    thermally-derated limits (battery.max_discharge_current_a/max_charge_current_a);
    a clipped step means the drive cycle's demanded power wasn't fully deliverable at
    that SOC/temperature, counted in power_limited_steps rather than silently absorbed.
    """
    t_s = np.asarray(t_s, dtype=float)
    v_mps = np.asarray(v_mps, dtype=float)
    if t_s.shape != v_mps.shape or t_s.size < 2:
        raise ValueError("t_s and v_mps must be equal-length arrays of at least 2 samples")
    if vehicle.battery_usable_kwh <= 0:
        raise ValueError("simulate_drive_cycle_with_battery requires vehicle.battery_usable_kwh > 0")

    if initial_state is None:
        initial_state = BatteryState(soc=vehicle.battery_max_soc, temperature_c=ambient_temp_c)

    accel = np.gradient(v_mps, t_s)
    n = len(t_s)

    soc_trace = np.empty(n)
    voltage_trace = np.empty(n)
    current_trace = np.empty(n)
    efficiency_trace = np.full(n, np.nan)

    state = initial_state
    soc_trace[0] = state.soc
    voltage_trace[0] = battery.open_circuit_voltage(vehicle, state.soc)
    current_trace[0] = 0.0

    power_limited_steps = 0

    for i in range(1, n):
        dt = t_s[i] - t_s[i - 1]
        v = v_mps[i]

        f_road = road_load_force(vehicle, v)
        f_total = f_road + vehicle.mass_kg * accel[i]
        p_wheel = f_total * v  # W; positive = traction, negative = regen braking

        torque_nm = motor.motor_shaft_torque_nm(vehicle, f_total)
        omega_rad_s = motor.motor_shaft_speed_rad_s(vehicle, v)
        eta = motor.motor_efficiency(vehicle, torque_nm, omega_rad_s)

        p_elec = (p_wheel / eta) if (p_wheel >= 0 and eta > 0) else (p_wheel * eta)

        ocv = battery.open_circuit_voltage(vehicle, state.soc)
        current_a = p_elec / ocv if ocv > 0 else 0.0

        i_max_discharge = battery.max_discharge_current_a(vehicle, state)
        i_max_charge = battery.max_charge_current_a(vehicle, state)
        if current_a > i_max_discharge:
            current_a = i_max_discharge
            power_limited_steps += 1
        elif current_a < -i_max_charge:
            current_a = -i_max_charge
            power_limited_steps += 1

        state = battery.step_soc(vehicle, state, current_a, dt)

        soc_trace[i] = state.soc
        voltage_trace[i] = battery.terminal_voltage(vehicle, state.soc, current_a)
        current_trace[i] = current_a
        efficiency_trace[i] = eta

    distance_km = np.trapezoid(v_mps, t_s) / 1000.0
    soc_used = soc_trace[0] - soc_trace[-1]
    usable_soc_span = vehicle.battery_max_soc - vehicle.battery_min_soc
    range_km = (distance_km / soc_used * usable_soc_span) if soc_used > 0 else float("inf")

    return {
        "soc_trace": soc_trace,
        "voltage_trace": voltage_trace,
        "current_trace": current_trace,
        "efficiency_trace": efficiency_trace,
        "final_state": state,
        "distance_km": distance_km,
        "soc_used": soc_used,
        "range_km": range_km,
        "power_limited_steps": power_limited_steps,
    }
