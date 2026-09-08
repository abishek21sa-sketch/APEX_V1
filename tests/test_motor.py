import pytest

from apex.physics import (
    VehicleParams,
    motor_base_speed_rad_s,
    motor_efficiency,
    motor_shaft_speed_rad_s,
    motor_shaft_torque_nm,
)


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
        max_motor_rpm=10000.0,
        drivetrain_efficiency=0.9,
        regen_efficiency=0.7,
        battery_usable_kwh=60.0,
    )
    defaults.update(overrides)
    return VehicleParams(**defaults)


def test_shaft_torque_and_speed_scale_through_gear_ratio_and_wheel_radius():
    car = _car(gear_ratio=8.0, wheel_radius_m=0.32)
    torque = motor_shaft_torque_nm(car, wheel_force_n=1600.0)
    assert torque == pytest.approx(1600.0 * 0.32 / 8.0)

    speed = motor_shaft_speed_rad_s(car, wheel_speed_mps=16.0)
    assert speed == pytest.approx(16.0 / 0.32 * 8.0)


def test_shaft_torque_sign_follows_wheel_force_sign():
    car = _car()
    assert motor_shaft_torque_nm(car, wheel_force_n=-500.0) < 0.0


def test_efficiency_is_zero_at_essentially_zero_power():
    car = _car()
    assert motor_efficiency(car, torque_nm=0.0, speed_rad_s=100.0) == 0.0
    assert motor_efficiency(car, torque_nm=100.0, speed_rad_s=0.0) == 0.0


def test_efficiency_bounded_between_zero_and_one():
    car = _car()
    base_speed = motor_base_speed_rad_s(car)
    for torque_frac in [0.01, 0.1, 0.3, 0.5, 0.77, 1.0]:
        for speed_frac in [0.01, 0.1, 0.5, 1.0, 1.5]:
            eta = motor_efficiency(car, car.motor_peak_torque_nm * torque_frac, base_speed * speed_frac)
            assert 0.0 <= eta <= 1.0


def test_efficiency_is_low_at_very_low_torque_higher_in_the_middle():
    # Fixed losses dominate a tiny useful output at very low torque -- a well-known
    # real-motor behavior (see motor.py's docstring for the verified peak location).
    car = _car()
    base_speed = motor_base_speed_rad_s(car)
    eta_low = motor_efficiency(car, car.motor_peak_torque_nm * 0.02, base_speed)
    eta_mid = motor_efficiency(car, car.motor_peak_torque_nm * 0.5, base_speed)
    assert eta_mid > eta_low


def test_efficiency_is_lower_at_low_speed_than_high_speed_for_the_same_torque():
    car = _car()
    base_speed = motor_base_speed_rad_s(car)
    torque = car.motor_peak_torque_nm * 0.5
    eta_low_speed = motor_efficiency(car, torque, base_speed * 0.1)
    eta_high_speed = motor_efficiency(car, torque, base_speed * 1.0)
    assert eta_high_speed > eta_low_speed


def test_efficiency_falls_back_to_flat_scalar_when_peak_torque_is_unset():
    car = _car(motor_peak_torque_nm=0.0, drivetrain_efficiency=0.85)
    assert motor_efficiency(car, torque_nm=50.0, speed_rad_s=10.0) == pytest.approx(0.85)
