import numpy as np
import pytest

from apex.design import (
    DesignCandidate,
    PlatformContext,
    build_vehicle,
    default_design_space,
    random_candidate,
)


def _candidate(**overrides) -> DesignCandidate:
    defaults = dict(
        battery_capacity_kwh=70.0,
        motor_power_kw=200.0,
        gear_ratio=9.0,
        drag_coefficient=0.26,
        frontal_area_m2=2.3,
        motor_architecture="pm_synchronous",
        battery_chemistry="nmc",
        num_motors="1",
        tire_choice="standard",
    )
    defaults.update(overrides)
    return DesignCandidate(**defaults)


def test_build_vehicle_mass_equals_glider_plus_battery_plus_motor_plus_tire_delta():
    candidate = _candidate()
    context = PlatformContext()
    vehicle, report = build_vehicle(candidate, context)

    assert report.battery_mass_kg == pytest.approx(70.0 * 6.0)  # nmc: 6.0 kg/kWh
    assert report.motor_mass_kg == pytest.approx(200.0 / 1.8)  # pm_synchronous: 1.8 kW/kg
    expected_total = context.glider_mass_kg + report.battery_mass_kg + report.motor_mass_kg + 0.0  # standard tire delta=0
    assert vehicle.mass_kg == pytest.approx(expected_total)
    assert report.total_mass_kg == pytest.approx(expected_total)


def test_build_vehicle_cost_equals_glider_plus_battery_plus_motor_plus_tire_delta():
    candidate = _candidate()
    context = PlatformContext()
    vehicle, report = build_vehicle(candidate, context)

    assert report.battery_cost == pytest.approx(70.0 * 128.0)  # nmc: $128/kWh
    assert report.motor_cost == pytest.approx(200.0 * 11.0)  # pm_synchronous: $11/kW
    expected_total = context.glider_manufacturing_cost + report.battery_cost + report.motor_cost + 0.0
    assert report.total_manufacturing_cost == pytest.approx(expected_total)


def test_second_motor_adds_overhead_mass_and_cost_without_changing_rated_power():
    single = _candidate(num_motors="1")
    dual = _candidate(num_motors="2")
    v_single, r_single = build_vehicle(single)
    v_dual, r_dual = build_vehicle(dual)

    assert v_single.motor_power_kw == v_dual.motor_power_kw == 200.0  # unchanged: still combined rating
    assert r_dual.motor_mass_kg > r_single.motor_mass_kg
    assert r_dual.motor_cost > r_single.motor_cost


def test_battery_chemistry_changes_mass_and_cost_tradeoff():
    nmc = _candidate(battery_chemistry="nmc")
    lfp = _candidate(battery_chemistry="lfp")
    v_nmc, r_nmc = build_vehicle(nmc)
    v_lfp, r_lfp = build_vehicle(lfp)

    assert r_lfp.battery_mass_kg > r_nmc.battery_mass_kg  # LFP: heavier per kWh
    assert r_lfp.battery_cost < r_nmc.battery_cost  # LFP: cheaper per kWh


def test_tire_choice_changes_rolling_resistance_and_friction_tradeoff():
    eco = _candidate(tire_choice="eco_low_rolling_resistance")
    performance = _candidate(tire_choice="performance")
    v_eco, _ = build_vehicle(eco)
    v_perf, _ = build_vehicle(performance)

    assert v_eco.rolling_resistance_coeff < v_perf.rolling_resistance_coeff
    assert v_eco.tire_friction_coeff < v_perf.tire_friction_coeff


def test_motor_peak_torque_is_derived_from_power_and_architecture_base_speed():
    candidate = _candidate(motor_power_kw=200.0, motor_architecture="pm_synchronous")
    vehicle, _ = build_vehicle(candidate)
    base_speed_rad_s = 5500.0 * 2.0 * np.pi / 60.0
    expected_torque = 200_000.0 / base_speed_rad_s
    assert vehicle.motor_peak_torque_nm == pytest.approx(expected_torque)


def test_built_vehicle_is_a_valid_vehicleparams_instance():
    candidate = _candidate()
    vehicle, _ = build_vehicle(candidate)
    assert vehicle.mass_kg > 0
    assert vehicle.battery_usable_kwh == 70.0


def test_random_candidate_respects_bounds_and_choices_and_is_reproducible_with_seed():
    space = default_design_space()
    rng1 = np.random.default_rng(42)
    rng2 = np.random.default_rng(42)
    c1 = random_candidate(space, rng1)
    c2 = random_candidate(space, rng2)
    assert c1 == c2  # same seed -> identical candidate

    space.validate_assignment(c1.as_dict())  # should not raise: bounds/choices respected


def test_random_candidates_vary_across_many_draws():
    space = default_design_space()
    rng = np.random.default_rng(7)
    candidates = [random_candidate(space, rng) for _ in range(20)]
    assert len({c.motor_architecture for c in candidates}) > 1
    assert len({round(c.battery_capacity_kwh, 3) for c in candidates}) > 1
