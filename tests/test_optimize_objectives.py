import pytest

from apex.design import DesignCandidate, build_vehicle
from apex.optimize import (
    default_objectives,
    maximize_highway_range,
    minimize_manufacturing_cost,
    minimize_mass,
    minimize_zero_to_sixty,
)


def _vehicle_and_report():
    candidate = DesignCandidate(
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
    return build_vehicle(candidate)


def test_minimize_cost_reads_from_buildup_report():
    vehicle, report = _vehicle_and_report()
    obj = minimize_manufacturing_cost()
    assert obj.raw_value(vehicle, report) == pytest.approx(report.total_manufacturing_cost)
    assert obj.signed_value(vehicle, report) == pytest.approx(report.total_manufacturing_cost)
    assert obj.minimize is True


def test_minimize_mass_reads_from_vehicle():
    vehicle, report = _vehicle_and_report()
    obj = minimize_mass()
    assert obj.raw_value(vehicle, report) == pytest.approx(vehicle.mass_kg)


def test_minimize_zero_to_sixty_is_positive_and_finite():
    vehicle, report = _vehicle_and_report()
    obj = minimize_zero_to_sixty()
    value = obj.raw_value(vehicle, report)
    assert 0.0 < value < 30.0


def test_maximize_range_signed_value_is_negated_raw_value():
    vehicle, report = _vehicle_and_report()
    obj = maximize_highway_range()
    raw = obj.raw_value(vehicle, report)
    signed = obj.signed_value(vehicle, report)
    assert obj.minimize is False
    assert raw > 0.0
    assert signed == pytest.approx(-raw)


def test_default_objectives_has_four_distinct_named_objectives():
    objectives = default_objectives()
    assert len(objectives) == 4
    assert len({o.name for o in objectives}) == 4
    assert sum(1 for o in objectives if not o.minimize) == 1  # exactly one maximize (range)
