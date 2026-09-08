import pytest

from apex.active_learning import compare_strategies, run_pool_based_learning
from apex.design import default_design_space
from apex.surrogate import TARGET_NAMES, sample_candidates


def test_rejects_unknown_strategy():
    space = default_design_space()
    initial = sample_candidates(space, 5, seed=1)
    pool = sample_candidates(space, 10, seed=2)
    test = sample_candidates(space, 5, seed=3)
    with pytest.raises(ValueError):
        run_pool_based_learning(space, 2, "zero_to_sixty_s", "greedy", initial, pool, test, 3, seed=1)


def test_rejects_more_iterations_than_pool_size():
    space = default_design_space()
    initial = sample_candidates(space, 5, seed=1)
    pool = sample_candidates(space, 5, seed=2)
    test = sample_candidates(space, 5, seed=3)
    with pytest.raises(ValueError):
        run_pool_based_learning(space, 2, "zero_to_sixty_s", "uncertainty", initial, pool, test, 10, seed=1)


def test_trajectories_have_expected_length_and_start_at_n_initial():
    space = default_design_space()
    initial = sample_candidates(space, 6, seed=1)
    pool = sample_candidates(space, 20, seed=2)
    test = sample_candidates(space, 8, seed=3)
    n_iterations = 5

    run = run_pool_based_learning(space, 2, "zero_to_sixty_s", "uncertainty", initial, pool, test, n_iterations, seed=1)

    assert len(run.n_evaluations) == n_iterations + 1
    assert len(run.r2) == n_iterations + 1
    assert run.n_evaluations[0] == 6
    assert run.n_evaluations[-1] == 6 + n_iterations
    assert run.n_evaluations == list(range(6, 6 + n_iterations + 1))


def test_chosen_candidates_are_distinct_and_match_iteration_count():
    space = default_design_space()
    initial = sample_candidates(space, 5, seed=1)
    pool = sample_candidates(space, 20, seed=2)
    test = sample_candidates(space, 5, seed=3)
    n_iterations = 6

    run = run_pool_based_learning(space, 2, "zero_to_sixty_s", "uncertainty", initial, pool, test, n_iterations, seed=1)

    assert len(run.chosen_candidates) == n_iterations
    assert len(set(run.chosen_candidates)) == n_iterations  # no candidate picked twice


def test_r2_values_are_finite():
    space = default_design_space()
    initial = sample_candidates(space, 5, seed=1)
    pool = sample_candidates(space, 15, seed=2)
    test = sample_candidates(space, 5, seed=3)

    run = run_pool_based_learning(space, 1, "mass_kg", "uncertainty", initial, pool, test, 4, seed=1)
    assert all(r2 == r2 for r2 in run.r2)  # NaN check: NaN != NaN
    assert all(abs(r2) < 1e6 for r2 in run.r2)  # sane finite range, not +-inf


def test_compare_strategies_uses_identical_budgets_for_both_runs():
    space = default_design_space()
    uncertainty_run, random_run = compare_strategies(
        space, target_index=2, target_name=TARGET_NAMES[2],
        n_initial=6, n_pool=25, n_test=8, n_iterations=5, seed=1,
    )
    assert uncertainty_run.n_evaluations == random_run.n_evaluations
    assert uncertainty_run.strategy == "uncertainty"
    assert random_run.strategy == "random"
    assert len(uncertainty_run.chosen_candidates) == len(random_run.chosen_candidates) == 5


def test_compare_strategies_is_reproducible_with_a_fixed_seed():
    space = default_design_space()
    kwargs = dict(target_index=1, target_name=TARGET_NAMES[1], n_initial=5, n_pool=20, n_test=5, n_iterations=4, seed=9)
    run1_unc, run1_rand = compare_strategies(space, **kwargs)
    run2_unc, run2_rand = compare_strategies(space, **kwargs)
    assert run1_unc.r2 == run2_unc.r2
    assert run1_rand.r2 == run2_rand.r2
