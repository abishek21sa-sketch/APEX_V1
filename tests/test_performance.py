import pytest

from apex.physics import VehicleParams, braking_distance_m, max_gradeability, top_speed_mps, zero_to_sixty_s
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


def test_more_power_is_faster_to_sixty():
    weak = _car(motor_power_kw=100.0, motor_peak_torque_nm=250.0)
    strong = _car(motor_power_kw=300.0, motor_peak_torque_nm=500.0)
    assert zero_to_sixty_s(strong) < zero_to_sixty_s(weak)


def test_heavier_car_is_slower_to_sixty():
    light = _car(mass_kg=1500.0)
    heavy = _car(mass_kg=2400.0)
    assert zero_to_sixty_s(heavy) > zero_to_sixty_s(light)


def test_zero_to_sixty_is_finite_for_a_reasonable_car():
    car = _car()
    t = zero_to_sixty_s(car)
    assert 0.0 < t < 30.0


def test_uphill_grade_slows_acceleration():
    car = _car()
    assert zero_to_sixty_s(car, grade=0.10) > zero_to_sixty_s(car, grade=0.0)


def test_top_speed_is_plausible_and_draggier_car_is_slower():
    slippery = _car(drag_coefficient=0.22)
    draggy = _car(drag_coefficient=0.40)
    v_slippery = top_speed_mps(slippery)
    v_draggy = top_speed_mps(draggy)
    assert v_draggy < v_slippery
    assert 20.0 < v_slippery < 100.0  # sane m/s range (~45-220 mph outer bound)


def test_gradeability_is_zero_or_positive_and_decreases_with_speed():
    car = _car()
    g_low_speed = max_gradeability(car, speed_mps=5.0)
    g_high_speed = max_gradeability(car, speed_mps=30.0)
    assert g_low_speed >= g_high_speed >= 0.0


def test_braking_distance_increases_with_initial_speed():
    car = _car()
    d_30 = braking_distance_m(car, 30.0 * MPH_TO_MPS)
    d_60 = braking_distance_m(car, 60.0 * MPH_TO_MPS)
    assert d_60 > d_30
    # Rough physical sanity: quadrupling speed should roughly quadruple pure-friction
    # braking distance (d ~ v^2), with aero assist pulling the ratio down a bit.
    assert 3.0 < d_60 / d_30 < 4.5


def test_more_grip_shortens_braking_distance():
    grippy = _car(tire_friction_coeff=1.0)
    slick = _car(tire_friction_coeff=0.5)
    v = 60.0 * MPH_TO_MPS
    assert braking_distance_m(grippy, v) < braking_distance_m(slick, v)
