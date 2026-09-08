"""Phase 3 demonstration: sample random points from the design space, build each
into a full vehicle via the mass/cost buildup, and check them against the
platform's own worked-example mission (a sub-$42k electric crossover, >=310mi
range, sub-6s 0-60).

    python scripts/phase3_report.py

This is deliberately NOT an optimizer -- Phase 3's job is the design-space
representation and constraint system, not searching it intelligently. Random
sampling here just demonstrates the representation is usable end to end: a
candidate -> a physically consistent VehicleParams -> a feasibility verdict with
margins, ready for Phase 4's actual optimizer (CasADi/pymoo/OR-Tools per the
roadmap) to search over instead of sampling blindly.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np  # noqa: E402

from apex.design import build_vehicle, default_design_space, example_crossover_mission, random_candidate  # noqa: E402


def main() -> None:
    space = default_design_space()
    mission = example_crossover_mission()
    rng = np.random.default_rng(20260825)

    print(f"Mission: {mission.name}")
    print(f"Design space: {len(space.continuous)} continuous + {len(space.discrete)} discrete variables\n")

    n_samples = 500
    feasible_rows = []
    for _ in range(n_samples):
        candidate = random_candidate(space, rng)
        vehicle, report = build_vehicle(candidate)
        results = mission.evaluate(vehicle, report)
        if mission.is_feasible(results):
            feasible_rows.append((candidate, vehicle, report, results))

    print(f"{len(feasible_rows)} / {n_samples} random candidates satisfy every requirement.\n")

    if feasible_rows:
        # Cheapest feasible candidate -- the kind of question Phase 4's optimizer
        # will answer properly; here it's just "best of what random sampling found."
        cheapest = min(feasible_rows, key=lambda row: row[2].total_manufacturing_cost)
        _print_candidate("Cheapest feasible candidate found", *cheapest[:3])

        longest_range = max(feasible_rows, key=lambda row: _range_value(row[3]))
        _print_candidate("Longest-range feasible candidate found", *longest_range[:3])

    # One hand-picked candidate, shown in full detail regardless of feasibility --
    # useful for seeing exactly which requirement(s) a near-miss design fails by.
    print("\n--- Hand-picked candidate, full detail ---")
    from apex.design import DesignCandidate

    hand_picked = DesignCandidate(
        battery_capacity_kwh=78.0,
        motor_power_kw=220.0,
        gear_ratio=8.5,
        drag_coefficient=0.24,
        frontal_area_m2=2.25,
        motor_architecture="pm_synchronous",
        battery_chemistry="lfp",
        num_motors="1",
        tire_choice="eco_low_rolling_resistance",
    )
    vehicle, report = build_vehicle(hand_picked)
    results = mission.evaluate(vehicle, report)
    _print_candidate("Hand-picked candidate", hand_picked, vehicle, report, show_results=results)


def _range_value(results) -> float:
    return next(r.value for r in results if r.name.startswith("range"))


def _print_candidate(label, candidate, vehicle, report, show_results=None) -> None:
    print(f"\n{label}:")
    print(
        f"  {candidate.battery_capacity_kwh:.0f}kWh {candidate.battery_chemistry.upper()} battery, "
        f"{candidate.motor_power_kw:.0f}kW {candidate.motor_architecture} x{candidate.num_motors}, "
        f"{candidate.tire_choice} tires, Cd={candidate.drag_coefficient:.2f}, "
        f"frontal={candidate.frontal_area_m2:.2f}m^2, gear={candidate.gear_ratio:.1f}:1"
    )
    print(
        f"  mass: {report.total_mass_kg:.0f}kg (battery {report.battery_mass_kg:.0f} + "
        f"motor {report.motor_mass_kg:.0f} + glider/tires remainder)"
    )
    print(f"  manufacturing cost: ${report.total_manufacturing_cost:,.0f}")
    if show_results is None:
        return
    for r in show_results:
        status = "PASS" if r.satisfied else "FAIL"
        sign = "+" if r.margin >= 0 else ""
        print(f"    [{status}] {r.name}: {r.value:.1f}{r.unit} (need {r.direction.value} {r.threshold:.1f}{r.unit}, margin {sign}{r.margin:.1f}{r.unit})")


if __name__ == "__main__":
    main()
