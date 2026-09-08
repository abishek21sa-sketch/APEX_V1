import pytest

from apex.physics import (
    BatteryState,
    VehicleParams,
    degrade_state_of_health,
    max_charge_current_a,
    max_discharge_current_a,
    open_circuit_voltage,
    step_soc,
    terminal_voltage,
)


def _car(**overrides) -> VehicleParams:
    defaults = dict(
        name="test-car",
        mass_kg=1800.0,
        drag_coefficient=0.28,
        frontal_area_m2=2.3,
        rolling_resistance_coeff=0.009,
        wheel_radius_m=0.32,
        tire_friction_coeff=0.9,
        motor_power_kw=150.0,
        motor_peak_torque_nm=350.0,
        gear_ratio=8.0,
        drivetrain_efficiency=0.9,
        regen_efficiency=0.7,
        battery_usable_kwh=60.0,
        battery_nominal_voltage_v=350.0,
        battery_internal_resistance_ohm=0.05,
        battery_max_c_rate_discharge=3.0,
        battery_max_c_rate_charge=1.5,
    )
    defaults.update(overrides)
    return VehicleParams(**defaults)


def test_rejects_inverted_soc_bounds():
    with pytest.raises(ValueError):
        _car(battery_min_soc=0.9, battery_max_soc=0.1)


def test_capacity_ah_is_derived_from_usable_kwh_and_voltage():
    car = _car(battery_usable_kwh=70.0, battery_nominal_voltage_v=350.0)
    assert car.battery_capacity_ah == pytest.approx(200.0)


def test_open_circuit_voltage_increases_with_soc():
    car = _car()
    assert open_circuit_voltage(car, 0.9) > open_circuit_voltage(car, 0.2)


def test_terminal_voltage_sags_under_discharge_and_rises_under_charge():
    car = _car()
    ocv = open_circuit_voltage(car, 0.5)
    assert terminal_voltage(car, 0.5, current_a=100.0) < ocv
    assert terminal_voltage(car, 0.5, current_a=-100.0) > ocv


def test_discharge_current_limit_scales_with_c_rate_and_capacity():
    small = _car(battery_usable_kwh=30.0)
    big = _car(battery_usable_kwh=90.0)
    state = BatteryState(soc=0.5, temperature_c=25.0)
    assert max_discharge_current_a(big, state) > max_discharge_current_a(small, state)


def test_discharge_current_derated_at_low_soc_and_cold_temperature():
    car = _car()
    nominal = max_discharge_current_a(car, BatteryState(soc=0.5, temperature_c=25.0))
    low_soc = max_discharge_current_a(car, BatteryState(soc=0.05, temperature_c=25.0))
    cold = max_discharge_current_a(car, BatteryState(soc=0.5, temperature_c=-10.0))
    assert low_soc < nominal
    assert cold < nominal


def test_cold_derates_charging_more_severely_than_discharging():
    # Real packs tolerate cold discharge (driving) far better than cold charging
    # (lithium plating risk is charging-specific) -- cold weather mainly costs EVs
    # charging speed and range, not driving power.
    car = _car()
    cold_state = BatteryState(soc=0.5, temperature_c=-15.0)
    nominal_state = BatteryState(soc=0.5, temperature_c=25.0)

    discharge_ratio = max_discharge_current_a(car, cold_state) / max_discharge_current_a(car, nominal_state)
    charge_ratio = max_charge_current_a(car, cold_state) / max_charge_current_a(car, nominal_state)

    assert discharge_ratio > charge_ratio
    assert discharge_ratio >= 0.5  # discharge floor is milder than charge's


def test_charge_current_tapers_near_full_soc():
    car = _car()
    mid_soc = max_charge_current_a(car, BatteryState(soc=0.5, temperature_c=25.0))
    near_full = max_charge_current_a(car, BatteryState(soc=0.98, temperature_c=25.0))
    assert near_full < mid_soc


def test_step_soc_discharges_and_charges_in_the_right_direction():
    car = _car()
    state = BatteryState(soc=0.5)
    discharged = step_soc(car, state, current_a=50.0, dt_s=60.0)
    charged = step_soc(car, state, current_a=-50.0, dt_s=60.0)
    assert discharged.soc < state.soc < charged.soc


def test_step_soc_clips_to_valid_range():
    car = _car()
    state = BatteryState(soc=0.01)
    depleted = step_soc(car, state, current_a=1000.0, dt_s=3600.0)
    assert depleted.soc == pytest.approx(0.0)


def test_degradation_disabled_by_default_zero_rate():
    car = _car(battery_fade_per_1000_ah_throughput=0.0)
    assert degrade_state_of_health(car, cumulative_throughput_ah=1_000_000.0) == 1.0


def test_degradation_reduces_state_of_health_with_throughput_and_is_floored():
    car = _car(battery_fade_per_1000_ah_throughput=0.001)
    soh_early = degrade_state_of_health(car, cumulative_throughput_ah=1_000.0)
    soh_late = degrade_state_of_health(car, cumulative_throughput_ah=10_000_000.0)
    assert soh_early < 1.0
    assert soh_late == pytest.approx(0.5)  # floored, not negative or zero


def test_repeated_cycling_measurably_reduces_state_of_health():
    car = _car(battery_fade_per_1000_ah_throughput=0.01)
    state = BatteryState(soc=0.9)
    for _ in range(200):
        state = step_soc(car, state, current_a=100.0, dt_s=3600.0)  # discharge
        state = step_soc(car, state, current_a=-100.0, dt_s=3600.0)  # recharge
    assert state.state_of_health < 1.0
    assert state.cumulative_throughput_ah > 0.0
