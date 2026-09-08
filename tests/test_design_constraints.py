import pytest

from apex.design import (
    DesignCandidate,
    Direction,
    Mission,
    build_vehicle,
    example_crossover_mission,
    max_acceleration_time_s,
    max_braking_distance_m,
    max_manufacturing_cost_usd,
    max_mass_kg,
    min_gradeability_pct,
    min_highway_range_mi,
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


def test_at_most_requirement_satisfied_when_value_under_threshold():
    vehicle, report = build_vehicle(_candidate())
    req = max_mass_kg(threshold_kg=vehicle.mass_kg + 100.0)
    result = req.evaluate(vehicle, report)
    assert result.satisfied
    assert result.margin == pytest.approx(100.0, abs=1.0)


def test_at_most_requirement_violated_when_value_over_threshold():
    vehicle, report = build_vehicle(_candidate())
    req = max_mass_kg(threshold_kg=vehicle.mass_kg - 100.0)
    result = req.evaluate(vehicle, report)
    assert not result.satisfied
    assert result.margin < 0.0


def test_at_least_requirement_satisfied_and_violated_correctly():
    vehicle, report = build_vehicle(_candidate(battery_capacity_kwh=90.0))
    generous = min_highway_range_mi(threshold_mi=1.0)
    demanding = min_highway_range_mi(threshold_mi=100_000.0)
    assert generous.evaluate(vehicle, report).satisfied
    assert not demanding.evaluate(vehicle, report).satisfied


def test_direction_enum_values_are_distinct():
    assert Direction.AT_MOST != Direction.AT_LEAST


def test_mission_is_feasible_true_when_all_requirements_pass():
    vehicle, report = build_vehicle(_candidate(battery_capacity_kwh=100.0, motor_power_kw=300.0))
    mission = Mission(
        name="trivially easy",
        requirements=[
            max_acceleration_time_s(60.0),
            min_highway_range_mi(1.0),
            max_mass_kg(100_000.0),
        ],
    )
    results = mission.evaluate(vehicle, report)
    assert Mission.is_feasible(results)


def test_mission_is_feasible_false_when_any_requirement_fails():
    vehicle, report = build_vehicle(_candidate())
    mission = Mission(
        name="one impossible requirement",
        requirements=[
            max_acceleration_time_s(60.0),
            max_mass_kg(0.001),  # impossible
        ],
    )
    results = mission.evaluate(vehicle, report)
    assert not Mission.is_feasible(results)
    assert sum(r.satisfied for r in results) == 1


def test_gradeability_and_braking_requirement_constructors_produce_evaluable_results():
    vehicle, report = build_vehicle(_candidate())
    grade_req = min_gradeability_pct(threshold_pct=1.0)
    brake_req = max_braking_distance_m(threshold_m=1000.0)
    assert grade_req.evaluate(vehicle, report).value > 0.0
    assert brake_req.evaluate(vehicle, report).value > 0.0


def test_manufacturing_cost_requirement_reads_from_buildup_report_not_vehicle():
    vehicle, report = build_vehicle(_candidate())
    req = max_manufacturing_cost_usd(threshold_usd=report.total_manufacturing_cost)
    result = req.evaluate(vehicle, report)
    assert result.value == pytest.approx(report.total_manufacturing_cost)
    assert result.satisfied  # exactly at threshold is still "at most"


def test_example_crossover_mission_has_three_requirements_and_evaluates():
    mission = example_crossover_mission()
    assert len(mission.requirements) == 3
    vehicle, report = build_vehicle(_candidate(battery_capacity_kwh=95.0, motor_power_kw=250.0))
    results = mission.evaluate(vehicle, report)
    assert len(results) == 3
    assert isinstance(Mission.is_feasible(results), bool)


def test_example_crossover_mission_cost_threshold_reflects_msrp_markup():
    lenient = example_crossover_mission(msrp_markup_factor=1.0)
    strict = example_crossover_mission(msrp_markup_factor=2.0)
    cost_req_lenient = next(r for r in lenient.requirements if r.name == "manufacturing cost")
    cost_req_strict = next(r for r in strict.requirements if r.name == "manufacturing cost")
    assert cost_req_lenient.threshold > cost_req_strict.threshold
