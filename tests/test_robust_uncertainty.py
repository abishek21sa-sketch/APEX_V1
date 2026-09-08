import numpy as np
import pytest

from apex.robust import Scenario, UncertaintyModel, nominal_scenario


def test_sample_stays_within_declared_ranges():
    model = UncertaintyModel()
    rng = np.random.default_rng(0)
    scenarios = model.sample_many(500, rng)
    for s in scenarios:
        assert model.payload_kg_range[0] <= s.payload_kg <= model.payload_kg_range[1]
        assert model.ambient_temp_c_range[0] <= s.ambient_temp_c <= model.ambient_temp_c_range[1]
        assert model.road_grade_range[0] <= s.road_grade <= model.road_grade_range[1]
        assert model.tire_wear_factor_range[0] <= s.tire_wear_factor <= model.tire_wear_factor_range[1]
        assert model.battery_soh_range[0] <= s.battery_soh <= model.battery_soh_range[1]


def test_sample_many_returns_requested_count():
    model = UncertaintyModel()
    rng = np.random.default_rng(1)
    assert len(model.sample_many(37, rng)) == 37


def test_sample_is_reproducible_with_seeded_rng():
    model = UncertaintyModel()
    s1 = model.sample(np.random.default_rng(42))
    s2 = model.sample(np.random.default_rng(42))
    assert s1 == s2


def test_samples_vary_across_draws():
    model = UncertaintyModel()
    rng = np.random.default_rng(2)
    scenarios = model.sample_many(20, rng)
    assert len({s.payload_kg for s in scenarios}) > 1


def test_nominal_scenario_is_the_no_stress_operating_point():
    s = nominal_scenario()
    assert s == Scenario(payload_kg=0.0, ambient_temp_c=25.0, road_grade=0.0, tire_wear_factor=1.0, battery_soh=1.0)
