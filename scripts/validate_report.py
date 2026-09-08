"""Phase 1 validation report: run the physics kernel against a few published EV specs
and print computed vs. published figures side by side.

    python scripts/validate_report.py

This is a human-readable companion to tests/test_validation.py's automated (loose-
tolerance) assertions -- see that file's docstring and tests/reference_vehicles.py's
docstring for why the tolerances here are generous and what the known mismatches
(software-limited top speed, EPA-vs-steady-highway range) mean.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "tests"))

from apex.physics import constant_speed_range_km, top_speed_mps, zero_to_sixty_s  # noqa: E402
from apex.physics.constants import MPH_TO_MPS, MPS_TO_MPH  # noqa: E402
from reference_vehicles import ALL_REFERENCE_VEHICLES  # noqa: E402


def pct_diff(computed: float, published: float) -> float:
    return (computed - published) / published * 100.0


def main() -> None:
    print(f"{'Vehicle':<32}{'Metric':<24}{'Computed':>12}{'Published':>12}{'Diff':>10}")
    print("-" * 90)
    for ref in ALL_REFERENCE_VEHICLES:
        p = ref.params

        t60 = zero_to_sixty_s(p)
        print(f"{p.name:<32}{'0-60 mph (s)':<24}{t60:>12.2f}{ref.published_0_60_s:>12.2f}{pct_diff(t60, ref.published_0_60_s):>9.1f}%")

        vmax_mph = top_speed_mps(p) * MPS_TO_MPH
        note = " *" if abs(pct_diff(vmax_mph, ref.published_top_speed_mph)) > 15.0 else ""
        print(
            f"{'':<32}{'Top speed (mph)':<24}{vmax_mph:>12.1f}{ref.published_top_speed_mph:>12.1f}"
            f"{pct_diff(vmax_mph, ref.published_top_speed_mph):>9.1f}%{note}"
        )

        range_mi = constant_speed_range_km(p, 65.0 * MPH_TO_MPS) * 0.621371
        print(
            f"{'':<32}{'Range @ 65mph (mi)':<24}{range_mi:>12.0f}{ref.published_epa_range_mi:>12.0f}"
            f"{pct_diff(range_mi, ref.published_epa_range_mi):>9.1f}%"
        )
        print(f"{'':<32}{ref.source_note}")
        print("-" * 90)

    print(
        "\n* Top speed is now bounded by max_motor_rpm (the motor's mechanical redline through "
        "a fixed single-speed gear ratio) rather than raw motor power -- on most production EVs "
        "that redline, not an arbitrary software cap, is the real limiter. Figures over 15% off "
        "reflect an imprecise max_motor_rpm/gear_ratio estimate for that vehicle (see "
        "reference_vehicles.py's docstring), not a road-load equation error.\n"
        "Range @ 65mph is a sustained-highway-speed estimate, not an EPA-equivalent figure "
        "(EPA range uses a weighted multi-cycle test procedure) -- it is expected to read "
        "somewhat below the published EPA rating."
    )


if __name__ == "__main__":
    main()
