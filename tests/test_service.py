import pytest
from fastapi.testclient import TestClient

from service.main import app

client = TestClient(app)


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


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_evaluate_returns_positive_finite_metrics():
    response = client.post("/evaluate", json=_candidate_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["mass_kg"] > 0
    assert body["manufacturing_cost_usd"] > 0
    assert 0 < body["zero_to_sixty_s"] < 60
    assert body["range_mi"] > 0
    assert "candidate(" in body["vehicle_name"]


def test_evaluate_cost_and_mass_breakdowns_sum_to_the_totals():
    response = client.post("/evaluate", json=_candidate_payload())
    body = response.json()
    cost = body["cost_breakdown"]
    mass = body["mass_breakdown"]
    assert cost["glider_usd"] + cost["battery_usd"] + cost["motor_usd"] + cost["tire_delta_usd"] == pytest.approx(
        cost["total_usd"]
    )
    assert mass["glider_kg"] + mass["battery_kg"] + mass["motor_kg"] + mass["tire_delta_kg"] == pytest.approx(
        mass["total_kg"]
    )
    assert cost["total_usd"] == pytest.approx(body["manufacturing_cost_usd"])
    assert mass["total_kg"] == pytest.approx(body["mass_kg"])


def test_evaluate_matches_direct_apex_call():
    from apex.design import DesignCandidate, PlatformContext, build_vehicle
    from apex.physics import constant_speed_range_km, zero_to_sixty_s
    from apex.physics.constants import MPH_TO_MPS

    payload = _candidate_payload(battery_capacity_kwh=85.0, motor_power_kw=250.0)
    response = client.post("/evaluate", json=payload)
    body = response.json()

    candidate = DesignCandidate(**payload)
    vehicle, report = build_vehicle(candidate, PlatformContext())
    assert body["mass_kg"] == pytest.approx(vehicle.mass_kg)
    assert body["manufacturing_cost_usd"] == pytest.approx(report.total_manufacturing_cost)
    assert body["zero_to_sixty_s"] == pytest.approx(zero_to_sixty_s(vehicle))
    assert body["range_mi"] == pytest.approx(constant_speed_range_km(vehicle, 65.0 * MPH_TO_MPS) * 0.621371)


def test_evaluate_rejects_unknown_motor_architecture():
    response = client.post("/evaluate", json=_candidate_payload(motor_architecture="warp_drive"))
    assert response.status_code == 422


def test_evaluate_rejects_nonpositive_battery_capacity():
    response = client.post("/evaluate", json=_candidate_payload(battery_capacity_kwh=-5.0))
    assert response.status_code == 422


def test_pareto_returns_points_matching_requested_mission():
    request = {
        "mission": {
            "name": "quick test mission",
            "requirements": [
                {"kind": "max_acceleration_time_s", "threshold": 60.0},
                {"kind": "min_highway_range_mi", "threshold": 1.0},
            ],
        },
        "pop_size": 8,
        "n_gen": 2,
        "seed": 1,
    }
    response = client.post("/pareto", json=request)
    assert response.status_code == 200
    body = response.json()
    assert body["n_points"] == len(body["points"])
    assert body["n_points"] > 0
    for point in body["points"]:
        assert "manufacturing cost" in point["objective_values"]
        assert "0-60 mph time" in point["objective_values"]


def test_pareto_rejects_unknown_requirement_kind():
    request = {
        "mission": {"name": "bad mission", "requirements": [{"kind": "warp_speed", "threshold": 1.0}]},
        "pop_size": 8,
        "n_gen": 2,
    }
    response = client.post("/pareto", json=request)
    assert response.status_code == 422


def test_requirement_kinds_lists_known_kinds():
    response = client.get("/requirement-kinds")
    assert response.status_code == 200
    kinds = response.json()
    assert "max_acceleration_time_s" in kinds
    assert "min_highway_range_mi" in kinds


def test_robust_requirement_kinds_is_a_subset_of_nominal_kinds():
    nominal = set(client.get("/requirement-kinds").json())
    robust = client.get("/robust-requirement-kinds").json()
    assert "max_acceleration_time_s" in robust
    assert "min_highway_range_mi" in robust
    assert "max_manufacturing_cost_usd" not in robust  # cost doesn't vary with scenario, see robust/requirements.py
    assert set(robust) <= nominal


def test_robust_check_reports_worse_or_equal_reliability_than_nominal():
    payload = {
        "candidate": _candidate_payload(),
        "requirements": [{"kind": "max_acceleration_time_s", "threshold": 8.0}],
        "n_samples": 100,
        "seed": 1,
    }
    response = client.post("/robust-check", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["robustly_feasible"], bool)
    assert body["n_samples"] == 100
    req = body["requirements"][0]
    assert req["name"] == "0-60 mph time"
    assert 0.0 <= req["fraction_satisfied"] <= 1.0
    assert req["satisfied"] == (req["fraction_satisfied"] >= req["reliability_target"])
    # worst_value comes from a sampled scenario, so it should never be strictly
    # better than the single nominal-conditions value for an AT_MOST metric.
    assert req["worst_value"] >= req["nominal_value"]


def test_robust_check_rejects_cost_as_unsupported():
    payload = {
        "candidate": _candidate_payload(),
        "requirements": [{"kind": "max_manufacturing_cost_usd", "threshold": 30000.0}],
    }
    response = client.post("/robust-check", json=payload)
    assert response.status_code == 422


def test_benchmark_vehicles_returns_real_market_data():
    response = client.get("/benchmark-vehicles")
    assert response.status_code == 200
    vehicles = response.json()
    assert len(vehicles) >= 90
    names = [v["name"] for v in vehicles]
    assert len(names) == len(set(names)), "duplicate vehicle names"
    for v in vehicles:
        assert v["epa_range_mi"] > 0
        assert v["msrp_usd"] > 0
        assert v["vehicle_type"]
        assert v["drivetrain"]


def test_design_space_metadata_matches_default_design_space():
    from apex.design import default_design_space

    response = client.get("/design-space")
    assert response.status_code == 200
    body = response.json()

    space = default_design_space()
    assert len(body["continuous"]) == len(space.continuous)
    assert len(body["discrete"]) == len(space.discrete)
    battery_var = next(v for v in body["continuous"] if v["name"] == "battery_capacity_kwh")
    assert battery_var["lower"] == pytest.approx(space["battery_capacity_kwh"].lower)
    assert battery_var["upper"] == pytest.approx(space["battery_capacity_kwh"].upper)
    architecture_var = next(v for v in body["discrete"] if v["name"] == "motor_architecture")
    assert set(architecture_var["choices"]) == set(space["motor_architecture"].choices)


def test_pareto_with_impossible_mission_returns_zero_points():
    request = {
        "mission": {"name": "impossible", "requirements": [{"kind": "max_mass_kg", "threshold": 0.001}]},
        "pop_size": 8,
        "n_gen": 2,
        "seed": 1,
    }
    response = client.post("/pareto", json=request)
    assert response.status_code == 200
    assert response.json()["n_points"] == 0
