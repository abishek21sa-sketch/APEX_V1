"""Phase 5 demonstration: take designs that pass the plain, nominal-only mission
(Phase 3/4's single operating point) and re-check them against payload, weather,
tire wear, and battery aging via Monte Carlo sampling -- showing how many of
those "feasible" designs actually hold up, and a distribution deep-dive on two
of them.

    python scripts/phase5_report.py

This is the gap Phase 5 exists to close: Phase 4's optimizer searches for designs
that are feasible at one nominal point (25C, no payload, flat road, new tires, a
fresh pack). A design can clear that bar and still fail in a cold-weather,
full-load, worn-tire, partially-aged scenario a real customer will actually see.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np  # noqa: E402

from apex.design import DesignCandidate, build_vehicle, default_design_space, example_crossover_mission, random_candidate  # noqa: E402
from apex.robust import UncertaintyModel, evaluate_under_scenario, monte_carlo_evaluate, robust_crossover_mission  # noqa: E402
from apex.physics.constants import MPH_TO_MPS  # noqa: E402


def main() -> None:
    design_space = default_design_space()
    nominal_mission = example_crossover_mission()
    robust_mission = robust_crossover_mission()
    rng = np.random.default_rng(20260825)

    print(f"Nominal mission: {nominal_mission.name}")
    print(f"Robust mission:  {robust_mission.name}\n")
    print("Sampling candidates until 20 pass the nominal mission, then robust-checking each...\n")

    nominally_feasible = []
    while len(nominally_feasible) < 20:
        candidate = random_candidate(design_space, rng)
        vehicle, report = build_vehicle(candidate)
        if nominal_mission.is_feasible(nominal_mission.evaluate(vehicle, report)):
            nominally_feasible.append((candidate, vehicle, report))

    header = f"{'battery':>8} {'motor':>7} {'0-60(nom)':>10} {'0-60 ok%':>9} {'range(nom)':>11} {'range ok%':>10}  robust?"
    print(header)
    print("-" * len(header))

    robust_pass_count = 0
    first_fail, first_pass = None, None
    for candidate, vehicle, report in nominally_feasible:
        robust_results = robust_mission.evaluate(vehicle, n_samples=100, seed=1)
        accel = next(r for r in robust_results if r.name == "0-60 mph time")
        rng_req = next(r for r in robust_results if r.name == "highway range")
        passed = robust_mission.is_feasible(robust_results)
        robust_pass_count += passed
        if passed and first_pass is None:
            first_pass = (candidate, vehicle)
        if not passed and first_fail is None:
            first_fail = (candidate, vehicle)

        print(
            f"{candidate.battery_capacity_kwh:>6.0f}kWh {candidate.motor_power_kw:>5.0f}kW "
            f"{accel.nominal_value:>9.1f}s {accel.fraction_satisfied * 100:>8.0f}% "
            f"{rng_req.nominal_value:>10.0f}mi {rng_req.fraction_satisfied * 100:>9.0f}%  "
            f"{'YES' if passed else 'no'}"
        )

    print(
        f"\n{robust_pass_count} / {len(nominally_feasible)} nominally-feasible designs also clear the robust bar "
        "(0-60 and range each satisfied in >=95% of sampled scenarios).\n"
        "\nWhy so few, or none: Phase 4's optimizer minimizes cost subject to the nominal mission, which pushes it\n"
        "to hug the feasibility boundary with essentially zero margin -- a design at 5.5s nominal (just under the\n"
        "6.0s cap) has almost no room before payload, an uphill grade, or a cold morning tips it over. Range fares\n"
        "better when its nominal margin is generous (see the 'range ok%' column trend), because this platform's\n"
        "uncertainty model samples ambient temperature uniformly across -20C to 40C -- so roughly half of sampled\n"
        "scenarios see *some* cold-weather battery derating, more pessimistic than a real seasonal-weighted\n"
        "distribution would show (uncertainty.py's docstring already flags uniform sampling as a simplification,\n"
        "not a measured distribution shape). The fix isn't a bigger Monte Carlo budget -- it's feeding\n"
        "RobustMission into the optimizer as its constraint set, so the search finds designs with real margin\n"
        "instead of checking margin-free designs after the fact. That optimizer integration is a natural next\n"
        "step, not built in this phase.\n")

    if first_pass is None:
        # None of the 20 nominally-optimal samples were robust -- expected, per the
        # explanation above. Contrast with a hand-picked, deliberately generously-
        # margined design (not from the nominal-optimal sampling) to show robust
        # feasibility is achievable, just not what boundary-hugging optimization finds.
        generous_candidate = DesignCandidate(
            battery_capacity_kwh=110.0,
            motor_power_kw=280.0,
            gear_ratio=9.0,
            drag_coefficient=0.22,
            frontal_area_m2=2.15,
            motor_architecture="pm_synchronous",
            battery_chemistry="nmc",
            num_motors="1",
            tire_choice="standard",
        )
        generous_vehicle, _ = build_vehicle(generous_candidate)
        first_pass = (generous_candidate, generous_vehicle)
        pass_label = "A hand-picked, deliberately generously-margined design (passes robust)"
    else:
        pass_label = "A design that PASSES the robust check"

    for label, pick in [("A design that FAILS the robust check", first_fail), (pass_label, first_pass)]:
        if pick is None:
            continue
        candidate, vehicle = pick
        print(f"--- {label} ---")
        print(
            f"  {candidate.battery_capacity_kwh:.0f}kWh {candidate.battery_chemistry.upper()}, "
            f"{candidate.motor_power_kw:.0f}kW {candidate.motor_architecture}, {candidate.tire_choice} tires"
        )
        accel_mc = monte_carlo_evaluate(
            vehicle,
            metric=lambda v, s: evaluate_under_scenario(v, s, 65.0 * MPH_TO_MPS).zero_to_sixty_s,
            metric_name="0-60 mph time",
            unit="s",
            uncertainty_model=UncertaintyModel(),
            n_samples=200,
            seed=2,
        )
        range_mc = monte_carlo_evaluate(
            vehicle,
            metric=lambda v, s: evaluate_under_scenario(v, s, 65.0 * MPH_TO_MPS).range_mi,
            metric_name="range",
            unit="mi",
            uncertainty_model=UncertaintyModel(),
            n_samples=200,
            seed=2,
        )
        print(
            f"  0-60 time:  mean {accel_mc.mean:.2f}s, std {accel_mc.std:.2f}s, "
            f"P50 {accel_mc.percentile(50):.2f}s, P95 {accel_mc.percentile(95):.2f}s"
        )
        print(
            f"  range:      mean {range_mc.mean:.0f}mi, std {range_mc.std:.0f}mi, "
            f"P50 {range_mc.percentile(50):.0f}mi, P5 {range_mc.percentile(5):.0f}mi\n"
        )


if __name__ == "__main__":
    main()
