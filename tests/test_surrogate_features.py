import numpy as np
import pytest

from apex.design import DesignCandidate, default_design_space
from apex.surrogate import encode_candidate, encode_candidates, feature_names


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


def test_feature_names_length_matches_encoding_length():
    space = default_design_space()
    names = feature_names(space)
    encoded = encode_candidate(_candidate(), space)
    assert len(names) == len(encoded)


def test_continuous_values_pass_through_unchanged():
    space = default_design_space()
    candidate = _candidate(battery_capacity_kwh=88.0, gear_ratio=7.5)
    names = feature_names(space)
    encoded = encode_candidate(candidate, space)
    assert encoded[names.index("battery_capacity_kwh")] == pytest.approx(88.0)
    assert encoded[names.index("gear_ratio")] == pytest.approx(7.5)


def test_num_motors_is_encoded_as_a_plain_number_not_one_hot():
    space = default_design_space()
    names = feature_names(space)
    assert "num_motors" in names
    assert "num_motors=1" not in names

    one_motor = encode_candidate(_candidate(num_motors="1"), space)
    two_motors = encode_candidate(_candidate(num_motors="2"), space)
    idx = names.index("num_motors")
    assert one_motor[idx] == pytest.approx(1.0)
    assert two_motors[idx] == pytest.approx(2.0)


def test_categorical_discrete_is_one_hot_with_exactly_one_active():
    space = default_design_space()
    names = feature_names(space)
    encoded = encode_candidate(_candidate(motor_architecture="induction"), space)
    arch_indices = [i for i, n in enumerate(names) if n.startswith("motor_architecture=")]
    assert len(arch_indices) == 3  # pm_synchronous, induction, switched_reluctance
    active = [encoded[i] for i in arch_indices]
    assert sum(active) == pytest.approx(1.0)
    assert encoded[names.index("motor_architecture=induction")] == pytest.approx(1.0)
    assert encoded[names.index("motor_architecture=pm_synchronous")] == pytest.approx(0.0)


def test_encode_candidates_stacks_rows_in_order():
    space = default_design_space()
    candidates = [_candidate(battery_capacity_kwh=v) for v in (40.0, 60.0, 80.0)]
    X = encode_candidates(candidates, space)
    names = feature_names(space)
    idx = names.index("battery_capacity_kwh")
    assert X.shape == (3, len(names))
    assert list(X[:, idx]) == pytest.approx([40.0, 60.0, 80.0])
