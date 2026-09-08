import pytest

from apex.design import ContinuousVariable, DesignSpace, DiscreteVariable


def test_continuous_variable_rejects_inverted_bounds():
    with pytest.raises(ValueError):
        ContinuousVariable("x", lower=10.0, upper=5.0)


def test_continuous_variable_contains_and_clip():
    v = ContinuousVariable("x", lower=0.0, upper=10.0)
    assert v.contains(5.0)
    assert not v.contains(11.0)
    assert v.clip(15.0) == 10.0
    assert v.clip(-5.0) == 0.0


def test_discrete_variable_rejects_duplicate_choices():
    with pytest.raises(ValueError):
        DiscreteVariable("chem", choices=["nmc", "nmc"])


def test_discrete_variable_rejects_empty_choices():
    with pytest.raises(ValueError):
        DiscreteVariable("chem", choices=[])


def test_discrete_variable_contains():
    v = DiscreteVariable("chem", choices=["nmc", "lfp"])
    assert v.contains("nmc")
    assert not v.contains("nimh")


def test_design_space_rejects_duplicate_variable_names():
    with pytest.raises(ValueError):
        DesignSpace(variables=[ContinuousVariable("x", 0.0, 1.0), ContinuousVariable("x", 0.0, 2.0)])


def test_design_space_splits_continuous_and_discrete():
    space = DesignSpace(
        variables=[
            ContinuousVariable("battery_kwh", 30.0, 120.0),
            DiscreteVariable("chemistry", ["nmc", "lfp"]),
        ]
    )
    assert [v.name for v in space.continuous] == ["battery_kwh"]
    assert [v.name for v in space.discrete] == ["chemistry"]


def test_design_space_getitem_by_name():
    space = DesignSpace(variables=[ContinuousVariable("battery_kwh", 30.0, 120.0)])
    assert space["battery_kwh"].upper == 120.0
    with pytest.raises(KeyError):
        space["nonexistent"]


def test_validate_assignment_catches_missing_and_out_of_range_and_invalid_choice():
    space = DesignSpace(
        variables=[
            ContinuousVariable("battery_kwh", 30.0, 120.0),
            DiscreteVariable("chemistry", ["nmc", "lfp"]),
        ]
    )
    with pytest.raises(ValueError):
        space.validate_assignment({"battery_kwh": 60.0})  # missing chemistry
    with pytest.raises(ValueError):
        space.validate_assignment({"battery_kwh": 200.0, "chemistry": "nmc"})  # out of bounds
    with pytest.raises(ValueError):
        space.validate_assignment({"battery_kwh": 60.0, "chemistry": "nimh"})  # invalid choice
    space.validate_assignment({"battery_kwh": 60.0, "chemistry": "nmc"})  # should not raise
