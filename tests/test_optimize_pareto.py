import pytest

from apex.design import Mission, build_vehicle, default_design_space, example_crossover_mission, max_mass_kg
from apex.optimize import default_objectives, run_pareto_search

# Small pop/generation counts throughout: these tests check plumbing correctness
# (feasibility, structure, reproducibility), not search quality -- that would need
# a far larger budget and doesn't belong in the unit-test suite.


def test_run_pareto_search_returns_only_feasible_points():
    mission = example_crossover_mission()
    result = run_pareto_search(
        default_design_space(), mission, default_objectives(), pop_size=12, n_gen=4, seed=1
    )
    assert result.points  # a reasonably loose mission should find at least some feasible designs
    for point in result.points:
        vehicle, report = build_vehicle(point.candidate)
        results = mission.evaluate(vehicle, report)
        assert Mission.is_feasible(results)


def test_run_pareto_search_objective_values_have_all_objective_names():
    objectives = default_objectives()
    result = run_pareto_search(
        default_design_space(), example_crossover_mission(), objectives, pop_size=12, n_gen=4, seed=1
    )
    assert result.points
    expected_names = {o.name for o in objectives}
    for point in result.points:
        assert set(point.objective_values.keys()) == expected_names


def test_run_pareto_search_is_reproducible_with_a_fixed_seed():
    args = (default_design_space(), example_crossover_mission(), default_objectives())
    result1 = run_pareto_search(*args, pop_size=10, n_gen=3, seed=42)
    result2 = run_pareto_search(*args, pop_size=10, n_gen=3, seed=42)
    assert len(result1.points) == len(result2.points)
    assert [p.candidate for p in result1.points] == [p.candidate for p in result2.points]


def test_run_pareto_search_returns_no_points_for_an_impossible_mission():
    impossible_mission = Mission(name="impossible", requirements=[max_mass_kg(threshold_kg=0.001)])
    result = run_pareto_search(
        default_design_space(), impossible_mission, default_objectives(), pop_size=10, n_gen=3, seed=1
    )
    assert result.points == []


def test_run_pareto_search_with_no_requirements_still_returns_points():
    empty_mission = Mission(name="no requirements", requirements=[])
    result = run_pareto_search(
        default_design_space(), empty_mission, default_objectives(), pop_size=10, n_gen=3, seed=1
    )
    assert result.points
