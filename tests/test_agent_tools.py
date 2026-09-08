import json

import pytest

from agent.tools import (
    TOOL_DISPATCH,
    _ROBUST_REQUIREMENT_BUILDERS,
    tool_check_mission,
    tool_evaluate_candidate,
    tool_get_design_space,
    tool_list_requirement_kinds,
    tool_robust_check,
    tool_run_pareto_search,
    tool_sensitivity_analysis,
)
from apex.design import DesignCandidate, PlatformContext, build_vehicle, default_design_space
from apex.physics import constant_speed_range_km, zero_to_sixty_s
from apex.physics.constants import MPH_TO_MPS
from service.mission_registry import REQUIREMENT_KINDS


def _candidate_payload(**overrides):
    payload = dict(
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
    payload.update(overrides)
    return payload


def test_all_tool_definitions_have_a_dispatch_function():
    from agent.tools import TOOL_DEFINITIONS

    names = {t["name"] for t in TOOL_DEFINITIONS}
    assert names == set(TOOL_DISPATCH.keys())


def test_get_design_space_matches_default_design_space():
    result = tool_get_design_space({})
    space = default_design_space()
    assert len(result["continuous"]) == len(space.continuous)
    assert len(result["discrete"]) == len(space.discrete)
    battery = next(v for v in result["continuous"] if v["name"] == "battery_capacity_kwh")
    assert battery["lower"] == pytest.approx(space["battery_capacity_kwh"].lower)


def test_list_requirement_kinds_matches_the_registry_and_flags_robust_support():
    result = tool_list_requirement_kinds({})
    kinds = {k["kind"] for k in result["kinds"]}
    assert kinds == set(REQUIREMENT_KINDS)
    by_kind = {k["kind"]: k for k in result["kinds"]}
    assert by_kind["max_acceleration_time_s"]["robust_supported"] is True
    assert by_kind["max_mass_kg"]["robust_supported"] is False


def test_evaluate_candidate_matches_a_direct_apex_call():
    payload = _candidate_payload(battery_capacity_kwh=85.0, motor_power_kw=250.0)
    result = tool_evaluate_candidate(payload)

    candidate = DesignCandidate(**payload)
    vehicle, report = build_vehicle(candidate, PlatformContext())
    assert result["mass_kg"] == pytest.approx(vehicle.mass_kg, abs=0.1)
    assert result["manufacturing_cost_usd"] == pytest.approx(report.total_manufacturing_cost, abs=0.01)
    assert result["zero_to_sixty_s"] == pytest.approx(zero_to_sixty_s(vehicle), abs=0.01)
    assert result["range_mi"] == pytest.approx(
        constant_speed_range_km(vehicle, 65.0 * MPH_TO_MPS) * 0.621371, abs=0.1
    )


def test_check_mission_reports_satisfied_and_margin():
    result = tool_check_mission(
        {
            "candidate": _candidate_payload(battery_capacity_kwh=100.0, motor_power_kw=300.0),
            "requirements": [
                {"kind": "max_acceleration_time_s", "threshold": 60.0},
                {"kind": "max_mass_kg", "threshold": 1.0},
            ],
        }
    )
    assert result["feasible"] is False
    by_name = {r["name"]: r for r in result["requirements"]}
    assert by_name["0-60 mph time"]["satisfied"] is True
    assert by_name["curb mass"]["satisfied"] is False
    assert by_name["curb mass"]["margin"] < 0


def test_run_pareto_search_returns_points_with_expected_shape():
    result = tool_run_pareto_search(
        {
            "requirements": [
                {"kind": "max_acceleration_time_s", "threshold": 60.0},
                {"kind": "min_highway_range_mi", "threshold": 1.0},
            ],
            "pop_size": 8,
            "n_gen": 2,
            "seed": 1,
        }
    )
    assert result["n_points"] == len(result["points"])
    assert result["n_points"] > 0
    point = result["points"][0]
    assert "candidate" in point and "objective_values" in point
    assert "manufacturing cost" in point["objective_values"]


def test_sensitivity_analysis_shows_range_increasing_with_battery_capacity():
    result = tool_sensitivity_analysis(
        {
            "base_candidate": _candidate_payload(),
            "field": "battery_capacity_kwh",
            "values": [40.0, 70.0, 100.0],
        }
    )
    ranges = [row["range_mi"] for row in result["results"]]
    assert ranges == sorted(ranges)  # strictly increasing battery -> increasing range


def test_sensitivity_analysis_rejects_unknown_field():
    with pytest.raises(ValueError):
        tool_sensitivity_analysis({"base_candidate": _candidate_payload(), "field": "warp_factor", "values": [1.0]})


def test_robust_check_matches_direct_robust_mission_evaluation():
    from apex.robust import RobustMission, UncertaintyModel

    payload = _candidate_payload(battery_capacity_kwh=100.0, motor_power_kw=280.0)
    requirements_spec = [{"kind": "max_acceleration_time_s", "threshold": 6.0}]
    result = tool_robust_check({"candidate": payload, "requirements": requirements_spec, "n_samples": 30, "seed": 1})

    candidate = DesignCandidate(**payload)
    vehicle, _ = build_vehicle(candidate, PlatformContext())
    mission = RobustMission(
        name="check", requirements=[_ROBUST_REQUIREMENT_BUILDERS["max_acceleration_time_s"](6.0)], uncertainty_model=UncertaintyModel()
    )
    direct_results = mission.evaluate(vehicle, n_samples=30, seed=1)

    assert result["requirements"][0]["fraction_satisfied"] == pytest.approx(direct_results[0].fraction_satisfied)
    assert result["robustly_feasible"] == RobustMission.is_feasible(direct_results)


def test_robust_check_rejects_unsupported_requirement_kind():
    with pytest.raises(ValueError):
        tool_robust_check(
            {
                "candidate": _candidate_payload(),
                "requirements": [{"kind": "max_mass_kg", "threshold": 1500.0}],
            }
        )


def test_every_tool_result_is_json_serializable():
    # This is exactly what engineer_agent._serialize() does with every tool's
    # output before sending it back to Claude as a tool_result -- a plain
    # `round(numpy_float, 2)` happens to survive json.dumps (numpy.float64
    # subclasses Python float), but numpy.bool_ does NOT subclass Python bool
    # and raises TypeError; this caught that exact bug in tool_check_mission
    # and tool_robust_check before either was ever exercised by a live LLM call.
    calls = {
        "get_design_space": {},
        "list_requirement_kinds": {},
        "evaluate_candidate": _candidate_payload(),
        "check_mission": {
            "candidate": _candidate_payload(),
            "requirements": [{"kind": "max_acceleration_time_s", "threshold": 6.0}],
        },
        "run_pareto_search": {
            "requirements": [{"kind": "max_acceleration_time_s", "threshold": 60.0}],
            "pop_size": 8,
            "n_gen": 2,
            "seed": 1,
        },
        "sensitivity_analysis": {"base_candidate": _candidate_payload(), "field": "battery_capacity_kwh", "values": [50.0, 80.0]},
        "robust_check": {
            "candidate": _candidate_payload(),
            "requirements": [{"kind": "max_acceleration_time_s", "threshold": 6.0}],
            "n_samples": 10,
        },
    }
    assert set(calls) == set(TOOL_DISPATCH)  # keep this test in sync with the tool set
    for name, tool_input in calls.items():
        result = TOOL_DISPATCH[name](tool_input)
        json.dumps(result)  # must not raise
