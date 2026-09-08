import pytest

from apex.physics import (
    VehicleParams,
    aero_drag_force,
    available_wheel_force,
    max_motor_speed_mps,
    max_traction_force,
    road_load_force,
)
from apex.physics.constants import MPH_TO_MPS


def _car(**overrides) -> VehicleParams:
    defaults = dict(
        name="test-car",
        mass_kg=1800.0,
        drag_coefficient=0.28,
        frontal_area_m2=2.3,
        rolling_resistance_coeff=0.009,
        wheel_radius_m=0.32,
        tire_friction_coeff=0.9,
        motor_power_kw=150.0,
        motor_peak_torque_nm=350.0,
        gear_ratio=8.0,
        drivetrain_efficiency=0.9,
        regen_efficiency=0.7,
        battery_usable_kwh=60.0,
    )
    defaults.update(overrides)
    return VehicleParams(**defaults)


def test_rejects_nonpositive_mass():
    with pytest.raises(ValueError):
        _car(mass_kg=0.0)


def test_aero_drag_scales_with_v_squared():
    car = _car()
    f10 = aero_drag_force(car, 10.0)
    f20 = aero_drag_force(car, 20.0)
    assert f20 == pytest.approx(f10 * 4, rel=1e-9)


def test_rolling_resistance_zero_at_standstill():
    car = _car()
    assert road_load_force(car, 0.0) == pytest.approx(0.0)


def test_road_load_increases_with_speed():
    car = _car()
    assert road_load_force(car, 30.0) > road_load_force(car, 10.0)


def test_uphill_grade_increases_road_load_downhill_decreases_it():
    car = _car()
    flat = road_load_force(car, 20.0, grade=0.0)
    uphill = road_load_force(car, 20.0, grade=0.06)
    downhill = road_load_force(car, 20.0, grade=-0.06)
    assert uphill > flat > downhill


def test_heavier_car_has_more_rolling_resistance():
    light = _car(mass_kg=1500.0)
    heavy = _car(mass_kg=2000.0)
    assert road_load_force(heavy, 20.0) > road_load_force(light, 20.0)


def test_available_force_capped_by_tire_traction_at_low_speed():
    car = _car(motor_peak_torque_nm=1000.0, gear_ratio=15.0)  # deliberately oversized motor
    assert available_wheel_force(car, 0.0) == pytest.approx(max_traction_force(car))


def test_available_force_drops_into_power_limited_region_at_high_speed():
    car = _car()
    f_low = available_wheel_force(car, 5.0)
    f_high = available_wheel_force(car, 40.0 * MPH_TO_MPS)
    assert f_high < f_low


def test_more_traction_coefficient_raises_traction_ceiling():
    grippy = _car(tire_friction_coeff=1.1)
    slick = _car(tire_friction_coeff=0.6)
    assert max_traction_force(grippy) > max_traction_force(slick)


def test_motor_force_drops_to_zero_beyond_rpm_redline():
    car = _car(max_motor_rpm=9000.0)
    v_redline = max_motor_speed_mps(car)
    assert available_wheel_force(car, v_redline * 0.99) > 0.0
    assert available_wheel_force(car, v_redline * 1.05) == pytest.approx(0.0)


def test_taller_gearing_raises_rpm_limited_top_speed():
    tall = _car(max_motor_rpm=9000.0, gear_ratio=6.0)
    short = _car(max_motor_rpm=9000.0, gear_ratio=10.0)
    assert max_motor_speed_mps(tall) > max_motor_speed_mps(short)
