"""Battery pack model: state of charge, terminal voltage via a single-resistor
(Rint) equivalent circuit, C-rate- and thermally-derated charge/discharge current
limits, and a simple cycle-throughput capacity-fade proxy.

    SOC_{t+1} = SOC_t - I_t * dt / (3600 * capacity_ah)
    V_terminal = OCV(SOC) - I * R_internal          (I > 0 on discharge)

Rint is the standard "basic state equation" tier the platform's engineering math
calls for; a full Thevenin (RC) transient model is a natural deepening once a use
case actually needs sub-second voltage-sag fidelity, not before. Likewise, pack
temperature here is an exogenous input (settable per call, e.g. by the eventual
robust-design/Monte-Carlo phase varying ambient conditions) rather than something
this module evolves from the battery's own I^2R heat -- self-heating is a natural
next slice, not included yet.
"""

from dataclasses import dataclass

import numpy as np

from .params import VehicleParams

# Open-circuit-voltage vs SOC, generic Li-ion (NMC/NCA-family) shape normalized to
# 1.0 at the pack's nominal voltage: flat middle plateau, steeper knees near empty
# and full. Not any specific cell's datasheet curve -- a representative shape.
_OCV_SOC_BREAKPOINTS = np.array([0.00, 0.05, 0.10, 0.20, 0.40, 0.60, 0.80, 0.90, 0.95, 1.00])
_OCV_SOC_FACTORS = np.array([0.88, 0.90, 0.93, 0.96, 0.99, 1.00, 1.02, 1.04, 1.06, 1.08])


@dataclass(frozen=True)
class BatteryState:
    soc: float  # 0..1
    temperature_c: float = 25.0
    cumulative_throughput_ah: float = 0.0  # running sum of |I|*dt, feeds the fade proxy
    state_of_health: float = 1.0  # fraction of original capacity remaining


def open_circuit_voltage(vehicle: VehicleParams, soc: float) -> float:
    factor = np.interp(soc, _OCV_SOC_BREAKPOINTS, _OCV_SOC_FACTORS)
    return vehicle.battery_nominal_voltage_v * factor


def terminal_voltage(vehicle: VehicleParams, soc: float, current_a: float) -> float:
    """current_a > 0 on discharge (terminal voltage sags below OCV), < 0 on
    charge/regen (terminal voltage rises above OCV)."""
    return open_circuit_voltage(vehicle, soc) - current_a * vehicle.battery_internal_resistance_ohm


def _thermal_derate_factor(temperature_c: float, is_discharge: bool) -> float:
    """1.0 in a nominal 15-35C band; tapering outside it, asymmetrically -- real
    packs tolerate cold *discharge* (driving) far better than cold *charge*
    (lithium plating risk is a charging-specific failure mode), which is why cold
    weather mainly costs EVs charging speed and range, not driving power. Floors
    at 0.5 for discharge vs. 0.2 for charge in the cold; both taper the same in
    the heat (thermal throttling to protect the pack applies either direction).
    A simplified stand-in for a real BMS thermal power-limit table either way.
    """
    if 15.0 <= temperature_c <= 35.0:
        return 1.0
    cold_floor = 0.5 if is_discharge else 0.2
    cold_slope = 0.5 if is_discharge else 0.8
    if temperature_c < 15.0:
        return max(cold_floor, 1.0 - (15.0 - temperature_c) / 25.0 * cold_slope)
    return max(0.2, 1.0 - (temperature_c - 35.0) / 10.0 * 0.8)


def _soc_derate_factor(soc: float, is_charging: bool) -> float:
    """Tapers charge current near full (CC/CV charge-curve behavior) and discharge
    current near empty (low-SOC power limiting), both typical BMS behavior.
    """
    if is_charging:
        if soc > 0.8:
            return max(0.1, 1.0 - (soc - 0.8) / 0.2 * 0.9)
        return 1.0
    if soc < 0.15:
        return max(0.1, soc / 0.15)
    return 1.0


def max_discharge_current_a(vehicle: VehicleParams, state: BatteryState) -> float:
    capacity_ah = vehicle.battery_capacity_ah * state.state_of_health
    c_rate_limit_a = vehicle.battery_max_c_rate_discharge * capacity_ah
    derate = _thermal_derate_factor(state.temperature_c, is_discharge=True) * _soc_derate_factor(state.soc, is_charging=False)
    return c_rate_limit_a * derate


def max_charge_current_a(vehicle: VehicleParams, state: BatteryState) -> float:
    capacity_ah = vehicle.battery_capacity_ah * state.state_of_health
    c_rate_limit_a = vehicle.battery_max_c_rate_charge * capacity_ah
    derate = _thermal_derate_factor(state.temperature_c, is_discharge=False) * _soc_derate_factor(state.soc, is_charging=True)
    return c_rate_limit_a * derate


def degrade_state_of_health(vehicle: VehicleParams, cumulative_throughput_ah: float) -> float:
    """Cycle-throughput capacity-fade proxy: state_of_health falls linearly with
    cumulative amp-hour throughput. This is a placeholder for the reliability/
    robust-design phases to build on, not a physically validated aging model --
    real fade depends on temperature history, C-rates, and calendar time too.
    Floored at 0.5 (a pack that faded further is past end-of-life, out of scope).
    """
    if vehicle.battery_fade_per_1000_ah_throughput <= 0:
        return 1.0
    fade = (cumulative_throughput_ah / 1000.0) * vehicle.battery_fade_per_1000_ah_throughput
    return max(0.5, 1.0 - fade)


def step_soc(vehicle: VehicleParams, state: BatteryState, current_a: float, dt_s: float) -> BatteryState:
    """Coulomb-count one timestep forward. current_a > 0 discharges, < 0 charges."""
    capacity_ah = vehicle.battery_capacity_ah * state.state_of_health
    new_soc = state.soc - current_a * dt_s / 3600.0 / capacity_ah
    new_throughput = state.cumulative_throughput_ah + abs(current_a) * dt_s / 3600.0
    return BatteryState(
        soc=float(np.clip(new_soc, 0.0, 1.0)),
        temperature_c=state.temperature_c,
        cumulative_throughput_ah=new_throughput,
        state_of_health=degrade_state_of_health(vehicle, new_throughput),
    )
