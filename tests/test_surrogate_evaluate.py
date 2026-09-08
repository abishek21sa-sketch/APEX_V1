import pytest

from apex.design import default_design_space
from apex.surrogate import TARGET_NAMES, generate_dataset, train_and_compare


def test_train_and_compare_returns_one_comparison_per_target():
    space = default_design_space()
    dataset = generate_dataset(space, n_samples=60, seed=1)
    comparisons = train_and_compare(dataset, test_size=0.25, seed=1)
    assert [c.target_name for c in comparisons] == TARGET_NAMES


def test_train_and_compare_metrics_are_finite_and_models_are_usable():
    space = default_design_space()
    dataset = generate_dataset(space, n_samples=60, seed=2)
    comparisons = train_and_compare(dataset, test_size=0.25, seed=2)
    for c in comparisons:
        assert c.gp_metrics.rmse >= 0.0
        assert c.rf_metrics.rmse >= 0.0
        # Fitted models should be directly reusable for new predictions.
        mean, std = c.gp_model.predict(dataset.X[:3])
        assert mean.shape == (3,)
        assert std.shape == (3,)


def test_train_and_compare_mass_target_fits_well_given_its_near_linear_structure():
    # Mass is (glider) + battery_kwh*specific_mass + motor_kw/specific_power +
    # tire_delta -- close to linear in the continuous inputs given a fixed
    # discrete combo, so a reasonably-sized dataset should fit it well; a good
    # sanity check that the whole pipeline (encoding -> fit -> predict) works
    # end to end, not just that it runs without crashing.
    space = default_design_space()
    dataset = generate_dataset(space, n_samples=150, seed=3)
    comparisons = train_and_compare(dataset, test_size=0.2, seed=3)
    mass_comparison = next(c for c in comparisons if c.target_name == "mass_kg")
    assert mass_comparison.gp_metrics.r2 > 0.8
    assert mass_comparison.rf_metrics.r2 > 0.8
