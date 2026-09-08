import numpy as np
import pytest

from apex.physics import (
    BatteryState,
    VehicleParams,
    constant_speed_range_km,
    simulate_drive_cycle,
    simulate_drive_cycle_with_battery,
)
from apex.physics.constants import MPH_TO_MPS
from apex.physics.drive_cycles import constant_speed_cycle, synthetic_urban_cycle


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
    )
    defaults.update(overrides)
    return VehicleParams(**defaults)


def test_rejects_mismatched_arrays():
    car = _car()
    with pytest.raises(ValueError):
        simulate_drive_cycle(car, [0.0, 1.0, 2.0], [0.0, 1.0])


def test_constant_speed_cycle_energy_matches_constant_speed_range():
    car = _car()
    speed = 65.0 * MPH_TO_MPS
    t, v = constant_speed_cycle(speed, duration_s=3600.0, dt=1.0)
    result = simulate_drive_cycle(car, t, v)
    range_from_sim_km = car.battery_usable_kwh / result["consumption_kwh_per_100km"] * 100.0
    range_from_closed_form_km = constant_speed_range_km(car, speed)
    assert range_from_sim_km == pytest.approx(range_from_closed_form_km, rel=0.02)


def test_range_decreases_at_higher_constant_speed_once_aero_dominates():
    car = _car()
    r_50 = constant_speed_range_km(car, 50.0 * MPH_TO_MPS)
    r_80 = constant_speed_range_km(car, 80.0 * MPH_TO_MPS)
    assert r_80 < r_50


def test_bigger_battery_gives_more_range_at_fixed_speed():
    small = _car(battery_usable_kwh=40.0)
    big = _car(battery_usable_kwh=80.0)
    speed = 60.0 * MPH_TO_MPS
    assert constant_speed_range_km(big, speed) > constant_speed_range_km(small, speed)


def test_stop_and_go_costs_more_energy_than_steady_cruise_at_same_average_speed():
    # Isolates the round-trip regen loss (drivetrain_efficiency * regen_efficiency < 1):
    # covering the same ground at the same average speed, accelerating/braking repeatedly
    # must cost more energy than one steady cruise, regardless of what that average speed
    # is or how it compares to some other cycle's speed.
    car = _car()
    t_city, v_city = synthetic_urban_cycle(n_repeats=10)
    stop_and_go = simulate_drive_cycle(car, t_city, v_city)

    avg_speed_mps = stop_and_go["avg_speed_kmh"] / 3.6
    t_steady, v_steady = constant_speed_cycle(avg_speed_mps, duration_s=stop_and_go["duration_s"], dt=1.0)
    steady_cruise = simulate_drive_cycle(car, t_steady, v_steady)

    assert stop_and_go["consumption_kwh_per_100km"] > steady_cruise["consumption_kwh_per_100km"]


def test_drive_cycle_distance_matches_expected_average_speed_character():
    t_city, v_city = synthetic_urban_cycle(n_repeats=10)
    city = simulate_drive_cycle(_car(), t_city, v_city)
    # Synthetic urban cycle is tuned toward a UDDS-like ~15-25 mph average -- not exact.
    assert 15.0 < city["avg_speed_kmh"] * 0.621371 < 25.0


def test_detailed_sim_requires_a_positive_battery_capacity():
    car = _car(battery_usable_kwh=0.0)
    t, v = constant_speed_cycle(20.0, duration_s=60.0, dt=1.0)
    with pytest.raises(ValueError):
        simulate_drive_cycle_with_battery(car, t, v)


def test_detailed_sim_drains_soc_over_a_normal_driving_cycle():
    car = _car()
    t, v = constant_speed_cycle(25.0, duration_s=1800.0, dt=1.0)
    result = simulate_drive_cycle_with_battery(car, t, v)
    assert result["soc_trace"][-1] < result["soc_trace"][0]
    assert result["soc_used"] > 0.0
    assert result["range_km"] > 0.0


def test_detailed_sim_roughly_agrees_with_flat_efficiency_model():
    # Two different-fidelity models of the same physical trip shouldn't diverge wildly:
    # broad cross-check, not a tight match (the motor efficiency map varies with load
    # instead of using a single flat scalar).
    car = _car()
    t, v = constant_speed_cycle(26.8, duration_s=1800.0, dt=1.0)  # ~60 mph

    flat = simulate_drive_cycle(car, t, v)
    detailed = simulate_drive_cycle_with_battery(car, t, v)

    detailed_energy_kwh = detailed["soc_used"] * car.battery_usable_kwh
    assert detailed_energy_kwh == pytest.approx(flat["energy_kwh"], rel=0.5)


def test_detailed_sim_reports_no_power_limiting_for_a_gentle_cycle_at_high_soc():
    car = _car()
    t, v = constant_speed_cycle(20.0, duration_s=120.0, dt=1.0)
    result = simulate_drive_cycle_with_battery(car, t, v, initial_state=BatteryState(soc=0.8))
    assert result["power_limited_steps"] == 0


def test_detailed_sim_flags_power_limiting_under_aggressive_demand_at_low_soc():
    car = _car()
    t = np.linspace(0.0, 10.0, 11)
    v = np.linspace(0.0, 30.0, 11)  # ~3 m/s^2, an aggressive launch
    result = simulate_drive_cycle_with_battery(car, t, v, initial_state=BatteryState(soc=0.05))
    assert result["power_limited_steps"] > 0


def test_detailed_sim_final_state_of_health_stays_in_valid_range():
    car = _car()
    t, v = constant_speed_cycle(25.0, duration_s=600.0, dt=1.0)
    result = simulate_drive_cycle_with_battery(car, t, v)
    assert 0.5 <= result["final_state"].state_of_health <= 1.0
    assert result["final_state"].cumulative_throughput_ah > 0.0
