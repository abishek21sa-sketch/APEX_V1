"""Phase 6 demonstration: generate a real simulation dataset (Latin Hypercube
Sampling over the design space, each point evaluated with the actual physics
kernel), train Gaussian Process and Random Forest surrogates against it, and
compare their held-out accuracy and prediction speed against the real physics.

    python scripts/phase6_report.py

The payoff this phase exists for: once fitted, a surrogate answers "what would
this candidate's cost/mass/0-60/range be?" in microseconds instead of the
milliseconds a real physics evaluation costs -- a difference that matters once
you're evaluating thousands of candidates (a large NSGA2 population/generation
budget, or Phase 5's Monte Carlo robustness sampling repeated per candidate).
"""

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np  # noqa: E402

from apex.design import build_vehicle, default_design_space  # noqa: E402
from apex.physics import constant_speed_range_km, zero_to_sixty_s  # noqa: E402
from apex.physics.constants import MPH_TO_MPS  # noqa: E402
from apex.surrogate import generate_dataset, train_and_compare  # noqa: E402


def main() -> None:
    design_space = default_design_space()
    n_samples = 400

    print(f"Generating a {n_samples}-point Latin Hypercube design-of-experiments dataset "
          f"(real physics evaluation per point)...")
    t0 = time.time()
    dataset = generate_dataset(design_space, n_samples=n_samples, seed=20260825)
    generation_time = time.time() - t0
    print(f"  done in {generation_time:.1f}s ({generation_time / n_samples * 1000:.2f}ms/candidate)\n")

    out_path = REPO_ROOT / "scratch_dataset.csv"
    dataset.save_csv(out_path)
    print(f"Saved to {out_path.name}\n")

    print("Training GP and Random Forest surrogates per target (80/20 train/test split)...\n")
    comparisons = train_and_compare(dataset, test_size=0.2, seed=1)

    header = f"{'target':<24}{'GP R2':>8}{'GP RMSE':>10}{'RF R2':>8}{'RF RMSE':>10}"
    print(header)
    print("-" * len(header))
    for c in comparisons:
        print(
            f"{c.target_name:<24}{c.gp_metrics.r2:>8.3f}{c.gp_metrics.rmse:>10.2f}"
            f"{c.rf_metrics.r2:>8.3f}{c.rf_metrics.rmse:>10.2f}"
        )

    # Speed comparison: real physics vs. the fitted range surrogate, same inputs.
    range_comparison = next(c for c in comparisons if c.target_name == "range_mi")
    n_speed_test = 200
    test_X = dataset.X[:n_speed_test]
    test_candidates = dataset.candidates[:n_speed_test]

    t0 = time.time()
    for candidate in test_candidates:
        vehicle, _ = build_vehicle(candidate)
        zero_to_sixty_s(vehicle)
        constant_speed_range_km(vehicle, 65.0 * MPH_TO_MPS)
    real_physics_time = time.time() - t0

    t0 = time.time()
    range_comparison.gp_model.predict(test_X)
    surrogate_time = time.time() - t0

    print(
        f"\n{n_speed_test} evaluations: real physics (0-60 + range) took {real_physics_time * 1000:.1f}ms "
        f"({real_physics_time / n_speed_test * 1e6:.0f}us/candidate); the fitted GP surrogate took "
        f"{surrogate_time * 1000:.2f}ms total ({surrogate_time / n_speed_test * 1e6:.1f}us/candidate) -- "
        f"~{real_physics_time / max(surrogate_time, 1e-9):.0f}x faster."
    )

    # Uncertainty preview for Phase 7: the GP's predictive std should be low near
    # densely-sampled training data and higher for a point well outside it.
    print("\nGP predictive uncertainty preview (range target, mi):")
    typical_point = dataset.X[0:1]
    extrapolated_point = typical_point * 3.0  # well outside the sampled design-space bounds
    mean_typical, std_typical = range_comparison.gp_model.predict(typical_point)
    mean_far, std_far = range_comparison.gp_model.predict(extrapolated_point)
    print(f"  a training-adjacent point:         predicted {mean_typical[0]:.0f} +/- {std_typical[0]:.1f} mi")
    print(f"  a point well outside the design space: predicted {mean_far[0]:.0f} +/- {std_far[0]:.1f} mi")
    print(
        "  (Phase 7's active-learning loop would use exactly this predictive std to pick which\n"
        "  untried candidate to actually simulate next -- highest uncertainty first -- instead of\n"
        "  the uniform Latin Hypercube sampling this phase used to build the initial dataset.)"
    )


if __name__ == "__main__":
    main()
