"""Phase 4 demonstration: run a real NSGA2 Pareto search over the Phase 3 design
space against the platform's own worked-example mission, and print the resulting
frontier -- this is what Phase 3's random sampling (phase3_report.py) was a
stand-in for.

    python scripts/phase4_report.py

The point isn't one "best" answer: cost, mass, 0-60 time, and range are made to
trade off against each other by construction (default_objectives()), so a
well-formed result is a spread of non-dominated designs, not a single winner --
exactly the platform proposal's "no single magic optimum" philosophy.
"""

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from apex.design import default_design_space, example_crossover_mission  # noqa: E402
from apex.optimize import default_objectives, run_pareto_search  # noqa: E402


def main() -> None:
    design_space = default_design_space()
    mission = example_crossover_mission()
    objectives = default_objectives()

    print(f"Mission: {mission.name}")
    print(f"Objectives: {[o.name for o in objectives]}")
    print("Running NSGA2 (pop_size=80, n_gen=30)...\n")

    t0 = time.time()
    result = run_pareto_search(design_space, mission, objectives, pop_size=80, n_gen=30, seed=20260825)
    elapsed = time.time() - t0

    print(f"Found {len(result.points)} non-dominated feasible designs in {elapsed:.1f}s.\n")
    if not result.points:
        print("No feasible designs found -- try loosening the mission's requirements.")
        return

    cost_name = "manufacturing cost"
    mass_name = "mass"
    accel_name = "0-60 mph time"
    range_name = next(k for k in result.points[0].objective_values if k.startswith("range"))

    points = sorted(result.points, key=lambda p: p.objective_values[cost_name])

    header = f"{'battery':>8} {'motor':>7} {'arch':>18} {'chem':>5} {'tire':>26} {'#m':>2}  {'cost':>9} {'mass':>7} {'0-60':>6} {'range':>7}"
    print(header)
    print("-" * len(header))
    for p in points:
        c = p.candidate
        ov = p.objective_values
        print(
            f"{c.battery_capacity_kwh:>6.0f}kWh {c.motor_power_kw:>5.0f}kW {c.motor_architecture:>18} "
            f"{c.battery_chemistry:>5} {c.tire_choice:>26} {c.num_motors:>2}  "
            f"${ov[cost_name]:>8,.0f} {ov[mass_name]:>6.0f}kg {ov[accel_name]:>5.1f}s {ov[range_name]:>6.0f}mi"
        )

    cheapest = min(points, key=lambda p: p.objective_values[cost_name])
    fastest = min(points, key=lambda p: p.objective_values[accel_name])
    longest_range = max(points, key=lambda p: p.objective_values[range_name])
    print(
        f"\nCheapest: ${cheapest.objective_values[cost_name]:,.0f}   "
        f"Fastest 0-60: {fastest.objective_values[accel_name]:.1f}s "
        f"(${fastest.objective_values[cost_name]:,.0f})   "
        f"Longest range: {longest_range.objective_values[range_name]:.0f}mi "
        f"(${longest_range.objective_values[cost_name]:,.0f})"
    )
    print(
        "\nNotice cost/range and cost/0-60 trade off across the table above -- the cheapest\n"
        "feasible design is not the fastest or longest-range one, and vice versa. That's the\n"
        "Pareto frontier working as intended: it hands an engineer the trade space, not a\n"
        "single verdict."
    )


if __name__ == "__main__":
    main()
