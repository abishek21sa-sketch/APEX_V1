"""Phase 1/2 exit criterion: "validate equations against published/reference vehicle
specifications." These checks are deliberately loose -- the kernel has no manufacturer
efficiency map, a single fixed gear ratio, and approximate (not manufacturer-confirmed)
torque/gear-ratio inputs for the reference vehicles. The goal is catching a wrong-shape
or order-of-magnitude physics bug, not reproducing a dyno sheet to the percent.
"""

import pytest

from apex.physics import BatteryState, constant_speed_range_km, simulate_drive_cycle_with_battery, top_speed_mps, zero_to_sixty_s
from apex.physics.constants import MPH_TO_MPS, MPS_TO_MPH
from apex.physics.drive_cycles import constant_speed_cycle

from reference_vehicles import ALL_REFERENCE_VEHICLES


@pytest.mark.parametrize("ref", ALL_REFERENCE_VEHICLES, ids=lambda r: r.params.name)
def test_zero_to_sixty_is_in_the_right_ballpark(ref):
    computed = zero_to_sixty_s(ref.params)
    assert computed == pytest.approx(ref.published_0_60_s, rel=0.35)


@pytest.mark.parametrize("ref", ALL_REFERENCE_VEHICLES, ids=lambda r: r.params.name)
def test_top_speed_is_in_the_right_ballpark(ref):
    # With max_motor_rpm modeling the real limiter (motor redline through a fixed
    # single-speed gear ratio, not an arbitrary software cap), computed top speed
    # should land close to the published figure.
    computed_mph = top_speed_mps(ref.params) * MPS_TO_MPH
    assert computed_mph == pytest.approx(ref.published_top_speed_mph, rel=0.20)


@pytest.mark.parametrize("ref", ALL_REFERENCE_VEHICLES, ids=lambda r: r.params.name)
def test_highway_range_is_a_plausible_fraction_of_epa_rating(ref):
    # Sustained 65 mph range typically undershoots the EPA combined rating (which blends
    # in more efficient city driving), so this checks "plausible fraction of," not "equal to."
    computed_mi = constant_speed_range_km(ref.params, 65.0 * MPH_TO_MPS) * 0.621371
    assert 0.45 * ref.published_epa_range_mi <= computed_mi <= 1.05 * ref.published_epa_range_mi


@pytest.mark.parametrize("ref", ALL_REFERENCE_VEHICLES, ids=lambda r: r.params.name)
def test_detailed_battery_sim_highway_range_is_also_in_the_right_ballpark(ref):
    # Same check as test_highway_range_is_a_plausible_fraction_of_epa_rating, but through
    # the Phase 2 motor-efficiency-map + battery-SOC path instead of the Phase 1 flat
    # scalar -- a regression guard for motor.py's power-normalization bug, where
    # referencing peak_torque * max_motor_rpm-implied speed (instead of peak_torque *
    # base_speed) overstated a 324kW-rated motor's implied peak power by >3x and
    # undershot range by ~45% instead of landing in this same plausible band.
    t, v = constant_speed_cycle(65.0 * MPH_TO_MPS, duration_s=3600.0, dt=1.0)
    result = simulate_drive_cycle_with_battery(
        ref.params, t, v, initial_state=BatteryState(soc=ref.params.battery_max_soc)
    )
    computed_mi = result["range_km"] * 0.621371
    assert 0.45 * ref.published_epa_range_mi <= computed_mi <= 1.05 * ref.published_epa_range_mi
