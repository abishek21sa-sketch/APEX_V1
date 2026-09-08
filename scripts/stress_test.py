"""Phase 10 stress test: cumulative memory pressure from running several
data-heavy operations back to back in one long-running Python process --
exactly the failure pattern documented in this user's sibling AirlinesApp
project (several Decision Center endpoints hit in sequence within one warm
process exhausting memory on a memory-constrained host, even though each
endpoint was fine in isolation). service/main.py runs as exactly this kind of
long-lived process, so it's worth checking proactively rather than finding out
after a deployment.

    python scripts/stress_test.py

Reports RSS memory after each operation in a realistic heavy sequence (large
Pareto searches, robust checks, dataset generation, an active-learning run) so
growth that plateaus (expected -- numpy/sklearn/pymoo working sets, not a leak)
is visible and distinguishable from growth that doesn't (a real problem).
"""

import gc
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np  # noqa: E402
import psutil  # noqa: E402

from apex.active_learning import compare_strategies  # noqa: E402
from apex.design import build_vehicle, default_design_space, example_crossover_mission, random_candidate  # noqa: E402
from apex.optimize import default_objectives, run_pareto_search  # noqa: E402
from apex.robust import robust_crossover_mission  # noqa: E402
from apex.surrogate import TARGET_NAMES, generate_dataset, train_and_compare  # noqa: E402

_PROCESS = psutil.Process()


def _rss_mb() -> float:
    gc.collect()
    return _PROCESS.memory_info().rss / (1024 * 1024)


def _step(label: str, fn) -> None:
    t0 = time.time()
    fn()
    elapsed = time.time() - t0
    print(f"  {label:<45} {_rss_mb():>8.1f} MB   ({elapsed:>5.1f}s)")


def main() -> None:
    design_space = default_design_space()
    mission = example_crossover_mission()
    objectives = default_objectives()

    print(f"Baseline RSS: {_rss_mb():.1f} MB\n")
    print("Running a heavy sequence in one process (mirrors several Decision-Center-")
    print("style endpoints hit back to back on a long-running service):\n")

    for i in range(3):
        _step(f"Pareto search #{i + 1} (pop=100, gen=30)", lambda: run_pareto_search(design_space, mission, objectives, pop_size=100, n_gen=30, seed=i))

    for i in range(5):
        candidate = random_candidate(design_space, np.random.default_rng(i))
        vehicle, _ = build_vehicle(candidate)
        _step(f"Robust check #{i + 1} (n_samples=200)", lambda v=vehicle, i=i: robust_crossover_mission().evaluate(v, n_samples=200, seed=i))

    for i in range(2):
        _step(f"Surrogate dataset generation #{i + 1} (n=400)", lambda i=i: generate_dataset(design_space, n_samples=400, seed=i))

    dataset = generate_dataset(design_space, n_samples=300, seed=99)
    _step("Surrogate train_and_compare (GP+RF x4 targets)", lambda: train_and_compare(dataset, seed=1))

    _step("Active learning (40 iterations, both strategies)", lambda: compare_strategies(
        design_space, target_index=TARGET_NAMES.index("zero_to_sixty_s"), target_name="zero_to_sixty_s",
        n_initial=10, n_pool=100, n_test=20, n_iterations=40, seed=1,
    ))

    final = _rss_mb()
    print(f"\nFinal RSS: {final:.1f} MB")


if __name__ == "__main__":
    main()
