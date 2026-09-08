import pytest

from apex.design import DesignSpace, ContinuousVariable, Mission, default_design_space, example_crossover_mission, max_mass_kg
from apex.optimize import ArchitectureProblem, default_objectives


def test_rejects_design_space_that_does_not_match_design_candidate_fields():
    mismatched_space = DesignSpace(variables=[ContinuousVariable("not_a_real_field", 0.0, 1.0)])
    with pytest.raises(ValueError):
        ArchitectureProblem(mismatched_space, example_crossover_mission(), default_objectives())


def test_rejects_empty_objectives():
    with pytest.raises(ValueError):
        ArchitectureProblem(default_design_space(), example_crossover_mission(), [])


def test_problem_dimensions_match_objectives_and_requirements_counts():
    mission = example_crossover_mission()
    objectives = default_objectives()
    problem = ArchitectureProblem(default_design_space(), mission, objectives)
    assert problem.n_obj == len(objectives) == 4
    assert problem.n_ieq_constr == len(mission.requirements) == 3


def test_problem_with_no_requirements_has_zero_constraints():
    empty_mission = Mission(name="no requirements", requirements=[])
    problem = ArchitectureProblem(default_design_space(), empty_mission, default_objectives())
    assert problem.n_ieq_constr == 0


def _sample_x():
    return {
        "battery_capacity_kwh": 78.0,
        "motor_power_kw": 220.0,
        "gear_ratio": 8.5,
        "drag_coefficient": 0.24,
        "frontal_area_m2": 2.25,
        "motor_architecture": "pm_synchronous",
        "battery_chemistry": "lfp",
        "num_motors": "1",
        "tire_choice": "eco_low_rolling_resistance",
    }


def test_to_candidate_round_trips_a_pymoo_style_x_dict():
    problem = ArchitectureProblem(default_design_space(), example_crossover_mission(), default_objectives())
    candidate = problem.to_candidate(_sample_x())
    assert candidate.battery_capacity_kwh == pytest.approx(78.0)
    assert candidate.motor_architecture == "pm_synchronous"


def test_evaluate_populates_f_with_one_value_per_objective():
    objectives = default_objectives()
    problem = ArchitectureProblem(default_design_space(), example_crossover_mission(), objectives)
    out = {}
    problem._evaluate(_sample_x(), out)
    assert len(out["F"]) == len(objectives)


def test_evaluate_g_sign_matches_pymoo_feasibility_convention():
    # A trivially satisfiable requirement should produce G <= 0 (pymoo: feasible);
    # a trivially impossible one should produce G > 0 (infeasible).
    easy_mission = Mission(name="easy", requirements=[max_mass_kg(threshold_kg=1_000_000.0)])
    impossible_mission = Mission(name="impossible", requirements=[max_mass_kg(threshold_kg=0.001)])

    easy_problem = ArchitectureProblem(default_design_space(), easy_mission, default_objectives())
    impossible_problem = ArchitectureProblem(default_design_space(), impossible_mission, default_objectives())

    out_easy, out_impossible = {}, {}
    easy_problem._evaluate(_sample_x(), out_easy)
    impossible_problem._evaluate(_sample_x(), out_impossible)

    assert out_easy["G"][0] <= 0.0
    assert out_impossible["G"][0] > 0.0
