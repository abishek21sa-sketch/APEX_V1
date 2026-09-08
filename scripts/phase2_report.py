"""Phase 2 demonstration: motor efficiency map shape, and battery SOC/voltage/
current behavior over a drive cycle, for the same reference vehicles Phase 1
validated against.

    python scripts/phase2_report.py

This isn't a spec-matching validation like scripts/validate_report.py (no
manufacturer publishes a motor efficiency map or a Wh/mi figure broken out by SOC
trajectory) -- it's a sanity demonstration that the new equivalent-circuit battery
model and torque/speed-aware motor efficiency map behave the way real ones do:
efficiency low at light load, SOC trending down over a normal drive (with small
regen upticks during braking), terminal voltage sagging under load and recovering
at rest.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "tests"))

from apex.physics import BatteryState, motor_base_speed_rad_s, motor_efficiency, simulate_drive_cycle_with_battery  # noqa: E402
from apex.physics.drive_cycles import synthetic_highway_cycle  # noqa: E402
from reference_vehicles import ALL_REFERENCE_VEHICLES  # noqa: E402


def report_motor_efficiency_map(vehicle) -> None:
    # Columns are fractions of base speed (where peak torque = rated power), not
    # the RPM redline -- see motor.py's docstring for why. >100% means operating
    # above base speed, in the field-weakening/constant-power region.
    base_speed = motor_base_speed_rad_s(vehicle)
    print(f"  Motor efficiency map ({vehicle.name}), % of (peak_torque, base_speed):")
    print("    torque\\speed  " + "".join(f"{int(sf*100):>6}%" for sf in [0.1, 0.25, 0.5, 1.0, 1.3]))
    for tf in [0.02, 0.1, 0.25, 0.41, 0.77, 1.0]:
        row = [motor_efficiency(vehicle, vehicle.motor_peak_torque_nm * tf, base_speed * sf) for sf in [0.1, 0.25, 0.5, 1.0, 1.3]]
        print(f"    {int(tf*100):>10}%  " + "".join(f"{e*100:>6.1f}%" for e in row))


def report_battery_trace(vehicle) -> None:
    t, v = synthetic_highway_cycle(n_repeats=8)
    result = simulate_drive_cycle_with_battery(vehicle, t, v, initial_state=BatteryState(soc=vehicle.battery_max_soc))
    soc = result["soc_trace"]
    voltage = result["voltage_trace"]
    print(f"  Highway drive-cycle battery trace ({vehicle.name}):")
    print(f"    distance: {result['distance_km']:.1f} km, SOC used: {result['soc_used']*100:.2f}%, "
          f"implied range: {result['range_km']:.0f} km ({result['range_km']*0.621371:.0f} mi)")
    # Not expected to be strictly monotonic: regen events during braking legitimately
    # nudge SOC up step to step even as the overall trend falls.
    print(f"    SOC:     {soc[0]*100:.1f}% -> {soc[-1]*100:.1f}% (min {soc.min()*100:.1f}%, max {soc.max()*100:.1f}%)")
    print(f"    voltage: min {voltage.min():.1f}V, max {voltage.max():.1f}V (nominal {vehicle.battery_nominal_voltage_v:.0f}V)")
    print(f"    power-limited steps: {result['power_limited_steps']} / {len(t)}")
    print(f"    final state of health: {result['final_state'].state_of_health*100:.3f}%")


def main() -> None:
    for ref in ALL_REFERENCE_VEHICLES:
        print(f"=== {ref.params.name} ===")
        report_motor_efficiency_map(ref.params)
        report_battery_trace(ref.params)
        print()


if __name__ == "__main__":
    main()
