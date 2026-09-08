import numpy as np
import pytest

from apex.design import DesignCandidate, Direction, build_vehicle, example_crossover_mission
from apex.robust import (
    RobustMission,
    RobustRequirement,
    UncertaintyModel,
    evaluate_under_scenario,
    monte_carlo_evaluate,
    nominal_scenario,
    robust_crossover_mission,
    robust_max_acceleration_time_s,
)
from apex.physics.constants import MPH_TO_MPS


def _vehicle(**overrides):
    defaults = dict(
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
    defaults.update(overrides)
    vehicle, _ = build_vehicle(DesignCandidate(**defaults))
    return vehicle


def test_monte_carlo_evaluate_returns_requested_sample_count_and_stats():
    vehicle = _vehicle()
    result = monte_carlo_evaluate(
        vehicle,
        metric=lambda v, s: evaluate_under_scenario(v, s, 65.0 * MPH_TO_MPS).zero_to_sixty_s,
        metric_name="0-60 mph time",
        unit="s",
        uncertainty_model=UncertaintyModel(),
        n_samples=60,
        seed=1,
    )
    assert len(result.samples) == 60
    assert result.mean > 0.0
    assert result.std >= 0.0
    assert result.percentile(50) == pytest.approx(np.median(result.samples))


def test_monte_carlo_evaluate_is_reproducible_with_a_fixed_seed():
    vehicle = _vehicle()
    kwargs = dict(
        metric=lambda v, s: evaluate_under_scenario(v, s, 65.0 * MPH_TO_MPS).range_mi,
        metric_name="range",
        unit="mi",
        uncertainty_model=UncertaintyModel(),
        n_samples=30,
        seed=7,
    )
    r1 = monte_carlo_evaluate(vehicle, **kwargs)
    r2 = monte_carlo_evaluate(vehicle, **kwargs)
    assert np.array_equal(r1.samples, r2.samples)


def _scenario_results_and_nominal(vehicle, n_samples, seed, speed_mps=65.0 * MPH_TO_MPS):
    rng = np.random.default_rng(seed)
    scenarios = UncertaintyModel().sample_many(n_samples, rng)
    scenario_results = [evaluate_under_scenario(vehicle, s, speed_mps) for s in scenarios]
    nominal_result = evaluate_under_scenario(vehicle, nominal_scenario(), speed_mps)
    return scenario_results, nominal_result


def test_robust_requirement_fully_satisfied_for_a_trivially_easy_threshold():
    vehicle = _vehicle()
    req = robust_max_acceleration_time_s(threshold_s=60.0, reliability_target=0.95)
    scenario_results, nominal_result = _scenario_results_and_nominal(vehicle, 40, seed=1)
    result = req.evaluate(scenario_results, nominal_result)
    assert result.fraction_satisfied == pytest.approx(1.0)
    assert result.satisfied


def test_robust_requirement_never_satisfied_for_an_impossible_threshold():
    vehicle = _vehicle()
    req = robust_max_acceleration_time_s(threshold_s=0.001, reliability_target=0.95)
    scenario_results, nominal_result = _scenario_results_and_nominal(vehicle, 40, seed=1)
    result = req.evaluate(scenario_results, nominal_result)
    assert result.fraction_satisfied == pytest.approx(0.0)
    assert not result.satisfied


def test_worst_value_matches_the_extreme_of_independently_recomputed_samples():
    vehicle = _vehicle()
    req = robust_max_acceleration_time_s(threshold_s=6.0)
    scenario_results, nominal_result = _scenario_results_and_nominal(vehicle, 25, seed=3)
    result = req.evaluate(scenario_results, nominal_result)
    recomputed = [sr.zero_to_sixty_s for sr in scenario_results]
    assert result.worst_value == pytest.approx(max(recomputed))  # AT_MOST -> worst is the max


def test_robust_requirement_direction_at_least_uses_min_as_worst_value():
    vehicle = _vehicle()
    req = RobustRequirement(
        name="range",
        direction=Direction.AT_LEAST,
        threshold=1.0,
        unit="mi",
        metric=lambda sr: sr.range_mi,
    )
    scenario_results, nominal_result = _scenario_results_and_nominal(vehicle, 25, seed=4)
    result = req.evaluate(scenario_results, nominal_result)
    recomputed = [sr.range_mi for sr in scenario_results]
    assert result.worst_value == pytest.approx(min(recomputed))


def test_robust_requirement_nominal_value_comes_from_the_nominal_scenario():
    req = RobustRequirement(name="range", direction=Direction.AT_LEAST, threshold=1.0, unit="mi", metric=lambda sr: sr.range_mi)
    vehicle = _vehicle()
    scenario_results, nominal_result = _scenario_results_and_nominal(vehicle, 10, seed=5)
    result = req.evaluate(scenario_results, nominal_result)
    assert result.nominal_value == pytest.approx(nominal_result.range_mi)


def test_robust_crossover_mission_has_two_requirements_no_cost():
    mission = robust_crossover_mission()
    assert len(mission.requirements) == 2
    assert all("cost" not in r.name for r in mission.requirements)


def test_a_generously_sized_vehicle_passes_the_robust_crossover_mission():
    vehicle = _vehicle(battery_capacity_kwh=110.0, motor_power_kw=280.0)
    mission = robust_crossover_mission()
    results = mission.evaluate(vehicle, n_samples=60, seed=1)
    assert mission.is_feasible(results)


_MARGINAL_CANDIDATE = DesignCandidate(
    battery_capacity_kwh=87.6,
    motor_power_kw=376.6,
    gear_ratio=6.83,
    drag_coefficient=0.324,
    frontal_area_m2=2.12,
    motor_architecture="switched_reluctance",
    battery_chemistry="lfp",
    num_motors="1",
    tire_choice="eco_low_rolling_resistance",
)


def test_nominally_feasible_but_marginal_vehicle_can_fail_the_robust_mission():
    # A vehicle tuned to just barely clear the plain (nominal-only) crossover
    # requirements can still fail once payload/cold/tire-wear/battery-aging are
    # allowed to vary -- that gap is the entire point of Phase 5.
    vehicle, report = build_vehicle(_MARGINAL_CANDIDATE)
    nominal_mission = example_crossover_mission()
    nominal_results = nominal_mission.evaluate(vehicle, report)
    robust_results = robust_crossover_mission().evaluate(vehicle, n_samples=60, seed=1)

    assert nominal_mission.is_feasible(nominal_results)  # passes at the single nominal point
    assert not robust_crossover_mission().is_feasible(robust_results)  # fails once conditions vary


def test_robust_mission_evaluate_matches_manual_requirement_evaluation():
    # Guards the shared-ScenarioResult refactor: RobustMission.evaluate() should
    # give identical results to evaluating each requirement against the same
    # scenario batch directly, just without redundant recomputation.
    vehicle = _vehicle()
    mission = RobustMission(
        name="check",
        requirements=[robust_max_acceleration_time_s(6.0)],
        uncertainty_model=UncertaintyModel(),
    )
    mission_results = mission.evaluate(vehicle, n_samples=20, seed=9)

    scenario_results, nominal_result = _scenario_results_and_nominal(vehicle, 20, seed=9, speed_mps=mission.highway_speed_mps)
    manual_result = mission.requirements[0].evaluate(scenario_results, nominal_result)

    assert mission_results[0] == manual_result
