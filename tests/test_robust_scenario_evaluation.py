import pytest

from apex.design import DesignCandidate, build_vehicle
from apex.robust import Scenario, apply_scenario, evaluate_under_scenario, nominal_scenario
from apex.physics.constants import MPH_TO_MPS


def _generously_sized_vehicle():
    # Big battery relative to motor power, so the battery's discharge-current limit
    # comfortably exceeds motor_power_kw at nominal conditions -- makes the "battery
    # doesn't bind at nominal" assertions below meaningful rather than accidental.
    candidate = DesignCandidate(
        battery_capacity_kwh=100.0,
        motor_power_kw=150.0,
        gear_ratio=9.0,
        drag_coefficient=0.24,
        frontal_area_m2=2.25,
        motor_architecture="pm_synchronous",
        battery_chemistry="nmc",
        num_motors="1",
        tire_choice="standard",
    )
    vehicle, _ = build_vehicle(candidate)
    return vehicle


def test_payload_increases_mass_by_exactly_the_payload():
    vehicle = _generously_sized_vehicle()
    scenario = Scenario(payload_kg=250.0, ambient_temp_c=25.0, road_grade=0.0, tire_wear_factor=1.0, battery_soh=1.0)
    scenario_vehicle, _ = apply_scenario(vehicle, scenario)
    assert scenario_vehicle.mass_kg == pytest.approx(vehicle.mass_kg + 250.0)


def test_tire_wear_raises_rolling_resistance_and_lowers_friction():
    vehicle = _generously_sized_vehicle()
    worn = Scenario(payload_kg=0.0, ambient_temp_c=25.0, road_grade=0.0, tire_wear_factor=1.2, battery_soh=1.0)
    scenario_vehicle, _ = apply_scenario(vehicle, worn)
    assert scenario_vehicle.rolling_resistance_coeff > vehicle.rolling_resistance_coeff
    assert scenario_vehicle.tire_friction_coeff < vehicle.tire_friction_coeff


def test_nominal_scenario_does_not_derate_motor_power_for_a_generously_sized_battery():
    vehicle = _generously_sized_vehicle()
    scenario_vehicle, _ = apply_scenario(vehicle, nominal_scenario())
    assert scenario_vehicle.motor_power_kw == pytest.approx(vehicle.motor_power_kw)


def test_cold_temperature_can_derate_motor_power_below_rated():
    vehicle = _generously_sized_vehicle()
    cold = Scenario(payload_kg=0.0, ambient_temp_c=-20.0, road_grade=0.0, tire_wear_factor=1.0, battery_soh=1.0)
    scenario_vehicle, _ = apply_scenario(vehicle, cold)
    assert scenario_vehicle.motor_power_kw <= vehicle.motor_power_kw


def test_battery_soh_scales_usable_energy_proportionally():
    vehicle = _generously_sized_vehicle()
    aged = Scenario(payload_kg=0.0, ambient_temp_c=25.0, road_grade=0.0, tire_wear_factor=1.0, battery_soh=0.85)
    scenario_vehicle, _ = apply_scenario(vehicle, aged)
    assert scenario_vehicle.battery_usable_kwh == pytest.approx(vehicle.battery_usable_kwh * 0.85)


def test_battery_state_reflects_scenario_temperature_and_soh():
    vehicle = _generously_sized_vehicle()
    scenario = Scenario(payload_kg=0.0, ambient_temp_c=-10.0, road_grade=0.0, tire_wear_factor=1.0, battery_soh=0.9)
    _, battery_state = apply_scenario(vehicle, scenario)
    assert battery_state.temperature_c == pytest.approx(-10.0)
    assert battery_state.state_of_health == pytest.approx(0.9)


def test_evaluate_under_scenario_returns_finite_positive_metrics():
    vehicle = _generously_sized_vehicle()
    result = evaluate_under_scenario(vehicle, nominal_scenario(), highway_speed_mps=65.0 * MPH_TO_MPS)
    assert 0.0 < result.zero_to_sixty_s < 60.0
    assert result.range_mi > 0.0
    assert result.braking_distance_m > 0.0


def test_uphill_grade_increases_zero_to_sixty_time():
    vehicle = _generously_sized_vehicle()
    flat = Scenario(payload_kg=0.0, ambient_temp_c=25.0, road_grade=0.0, tire_wear_factor=1.0, battery_soh=1.0)
    uphill = Scenario(payload_kg=0.0, ambient_temp_c=25.0, road_grade=0.06, tire_wear_factor=1.0, battery_soh=1.0)
    r_flat = evaluate_under_scenario(vehicle, flat, highway_speed_mps=65.0 * MPH_TO_MPS)
    r_uphill = evaluate_under_scenario(vehicle, uphill, highway_speed_mps=65.0 * MPH_TO_MPS)
    assert r_uphill.zero_to_sixty_s > r_flat.zero_to_sixty_s


def test_payload_reduces_range():
    vehicle = _generously_sized_vehicle()
    light = Scenario(payload_kg=0.0, ambient_temp_c=25.0, road_grade=0.0, tire_wear_factor=1.0, battery_soh=1.0)
    loaded = Scenario(payload_kg=400.0, ambient_temp_c=25.0, road_grade=0.0, tire_wear_factor=1.0, battery_soh=1.0)
    r_light = evaluate_under_scenario(vehicle, light, highway_speed_mps=65.0 * MPH_TO_MPS)
    r_loaded = evaluate_under_scenario(vehicle, loaded, highway_speed_mps=65.0 * MPH_TO_MPS)
    assert r_loaded.range_mi < r_light.range_mi
