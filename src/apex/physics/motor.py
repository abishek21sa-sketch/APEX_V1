"""Motor + inverter efficiency map: a physically-motivated loss decomposition
(fixed iron/friction loss, copper I^2R loss scaling with torque^2, switching/iron
loss scaling with speed) instead of the flat drivetrain_efficiency scalar the
Phase 1 kernel uses for its coarse force-availability and energy checks.

    P_loss(T, w) = P_fixed + k_copper * T^2 + k_iron * |w|
    eta = P_mech / (P_mech + P_loss),  P_mech = T * w

This produces the qualitative shape real traction-motor efficiency maps show: poor
efficiency at low torque/low speed (fixed loss dominates a small useful output), a
broad high-efficiency region at moderate-to-high torque and speed, and a mild
falloff approaching peak torque (copper loss starts to bite).

Coefficients are expressed as fractions of the vehicle's own rated power
(motor_power_kw), referenced against motor_base_speed_rad_s() -- the speed at
which full peak torque produces exactly rated power (P = T*w), i.e. where the
motor's constant-torque region meets its constant-power region. This, not
max_motor_rpm's redline, is the correct "100%" reference point for a loss model:
peak_torque * base_speed is exactly rated power by construction, whereas
peak_torque * redline speed is not physically achievable (for the Tesla reference
vehicle it implies a ~1063kW peak, over 3x the real 324kW rating) and badly
overstated fixed/iron losses at realistic light-load operating points. This
module's coefficients describe one representative "good EV traction motor"
shape, not any specific motor's dyno map, and don't model a multi-motor vehicle
disengaging one motor at light load (a real Tesla dual-motor behavior) -- both
are Phase 2+ simplifications.

Verified numerically (not just asserted; see scripts/phase2_report.py): with the
coefficients below, efficiency peaks at ~97.1% around 41% peak torque at base
speed; at the (peak_torque, base_speed) rated point it's ~96.0%. For the Tesla
reference vehicle at a steady 65mph highway cruise (torque ~2.8% of peak, in the
field-weakening region ~33% above base speed), average efficiency comes out to
~83.9%, giving a simulated range of ~329mi against an EPA rating of 353mi and
this kernel's own flat-efficiency-model estimate of ~369mi at the same speed (see
tests/test_validation.py's analogous check on the flat model) -- landing within
~7% of published, not the ~45% undershoot an earlier (buggy) normalization
produced by referencing peak_torque * max_motor_rpm-implied speed instead of
peak_torque * base_speed (the former implied a ~1063kW peak for a 324kW-rated
motor).

This module is additive: energy.simulate_drive_cycle_with_battery() uses it; the
original Phase 1 energy.simulate_drive_cycle() keeps using the flat
drivetrain_efficiency scalar, so its already-validated behavior
(tests/test_validation.py) is untouched.
"""

import numpy as np

from .params import VehicleParams

# Loss coefficients as fractions of rated power (motor_power_kw), referenced
# against (peak_torque, base_speed) -- see module docstring.
_FIXED_LOSS_FRACTION = 0.003
_COPPER_LOSS_FRACTION = 0.036  # loss at 100% of peak torque
_IRON_LOSS_FRACTION = 0.003  # loss at 100% of base speed


def motor_peak_speed_rad_s(vehicle: VehicleParams) -> float:
    """Speed at the motor's RPM redline (max_motor_rpm) -- the real top-speed
    limiter (see longitudinal.max_motor_speed_mps), not the efficiency model's
    reference point (see motor_base_speed_rad_s).
    """
    return vehicle.max_motor_rpm * 2.0 * np.pi / 60.0


def motor_base_speed_rad_s(vehicle: VehicleParams) -> float:
    """Speed at which full peak_torque produces exactly rated power (motor_power_kw)
    -- the corner where the motor's constant-torque region meets its constant-power
    region, and this module's efficiency-map reference point.
    """
    if vehicle.motor_peak_torque_nm <= 0:
        return 0.0
    return vehicle.motor_power_kw * 1000.0 / vehicle.motor_peak_torque_nm


def motor_shaft_torque_nm(vehicle: VehicleParams, wheel_force_n: float) -> float:
    """Torque at the motor shaft implied by a wheel force (sign preserved: negative
    wheel_force_n, e.g. under regen braking, gives negative motor torque)."""
    return wheel_force_n * vehicle.wheel_radius_m / vehicle.gear_ratio


def motor_shaft_speed_rad_s(vehicle: VehicleParams, wheel_speed_mps: float) -> float:
    return wheel_speed_mps / vehicle.wheel_radius_m * vehicle.gear_ratio


def motor_efficiency(vehicle: VehicleParams, torque_nm: float, speed_rad_s: float) -> float:
    """Fraction of mechanical power actually drawn as electrical power (motoring,
    P_mech > 0) or actually returned to the battery (generating, P_mech < 0) --
    i.e. always < 1 in either direction, just speed/torque-aware instead of flat.
    """
    peak_torque = vehicle.motor_peak_torque_nm
    peak_power_w = vehicle.motor_power_kw * 1000.0
    base_speed = motor_base_speed_rad_s(vehicle)
    if peak_torque <= 0 or peak_power_w <= 0:
        return vehicle.drivetrain_efficiency

    p_mech = abs(torque_nm * speed_rad_s)
    if p_mech < 1e-6 * peak_power_w:
        return 0.0  # no meaningful efficiency figure at ~zero power

    p_fixed = _FIXED_LOSS_FRACTION * peak_power_w
    k_copper = _COPPER_LOSS_FRACTION * peak_power_w / peak_torque**2
    k_iron = _IRON_LOSS_FRACTION * peak_power_w / base_speed

    p_loss = p_fixed + k_copper * torque_nm**2 + k_iron * abs(speed_rad_s)
    eta = p_mech / (p_mech + p_loss)
    return float(np.clip(eta, 0.05, 0.98))
