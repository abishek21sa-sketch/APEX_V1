"""Pool-based active-learning loop: maintain a large pool of unevaluated candidate
designs (sampled the same LHS+discrete-crossing way Phase 6's dataset generation
uses), and at each iteration pick the pool candidate the current GP surrogate is
most uncertain about, evaluate it with the real physics kernel -- the expensive
step this whole loop exists to spend as few times as possible on -- and refit.

    simulate -> learn -> identify uncertainty -> choose experiment -> simulate ->
    update model -> optimize

per the platform proposal's own description of what active learning should give
this project: "a genuine autonomous engineering loop." Real physics is evaluated
lazily, only for the specific candidate chosen each iteration, never for the whole
pool up front -- this platform's physics kernel happens to be fast, but the whole
point of active learning is minimizing calls to whatever the ground-truth
evaluator costs (a full CFD run, an FEA crash simulation), so the loop is built to
behave correctly if that evaluator gets much more expensive later, not just to
work for this one.

compare_strategies() runs uncertainty-driven selection against a random-selection
baseline sharing the identical initial set, pool, held-out test set, and iteration
budget, so any accuracy difference is attributable to the selection strategy, not
to different data.
"""

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from ..design import DesignCandidate, PlatformContext
from ..design.variables import DesignSpace
from ..surrogate import GPSurrogate, evaluate_candidates, evaluate_surrogate, sample_candidates
from ..surrogate.features import encode_candidates

STRATEGIES = ("uncertainty", "random")


def select_next_index(model: GPSurrogate, remaining_X: np.ndarray, strategy: str, rng: np.random.Generator) -> int:
    """The one-line decision this whole phase exists to make well: which pool
    candidate is worth spending the next real physics evaluation on. "uncertainty"
    picks whichever point the current surrogate is least sure about (highest
    predicted std); "random" ignores the surrogate entirely, for the baseline
    comparison.
    """
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy {strategy!r}, expected one of {STRATEGIES}")
    if strategy == "uncertainty":
        _, std = model.predict(remaining_X)
        return int(np.argmax(std))
    return int(rng.integers(len(remaining_X)))


@dataclass(frozen=True)
class ActiveLearningRun:
    strategy: str
    target_name: str
    n_evaluations: List[int]  # total real physics evaluations spent at each checkpoint (x-axis)
    r2: List[float]  # held-out R2 at each checkpoint (y-axis), same length as n_evaluations
    chosen_candidates: List[DesignCandidate]  # candidates picked during the loop, in selection order


def run_pool_based_learning(
    design_space: DesignSpace,
    target_index: int,
    target_name: str,
    strategy: str,
    initial_candidates: List[DesignCandidate],
    pool_candidates: List[DesignCandidate],
    test_candidates: List[DesignCandidate],
    n_iterations: int,
    seed: int,
    context: PlatformContext = PlatformContext(),
) -> ActiveLearningRun:
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy {strategy!r}, expected one of {STRATEGIES}")
    if n_iterations > len(pool_candidates):
        raise ValueError(
            f"n_iterations ({n_iterations}) cannot exceed the candidate pool size ({len(pool_candidates)})"
        )

    rng = np.random.default_rng(seed)

    X_train = encode_candidates(initial_candidates, design_space)
    y_train = evaluate_candidates(initial_candidates, context)[:, target_index]
    n_trained = len(initial_candidates)

    X_test = encode_candidates(test_candidates, design_space)
    y_test = evaluate_candidates(test_candidates, context)[:, target_index]

    remaining_candidates = list(pool_candidates)
    remaining_X = encode_candidates(remaining_candidates, design_space)

    n_evaluations, r2, chosen = [], [], []

    model = GPSurrogate(seed=seed)
    model.fit(X_train, y_train)
    n_evaluations.append(n_trained)
    r2.append(evaluate_surrogate(model, X_test, y_test).r2)

    for _ in range(n_iterations):
        pick = select_next_index(model, remaining_X, strategy, rng)

        picked_candidate = remaining_candidates.pop(pick)
        picked_x = remaining_X[pick]
        remaining_X = np.delete(remaining_X, pick, axis=0)
        picked_y = evaluate_candidates([picked_candidate], context)[0, target_index]

        X_train = np.vstack([X_train, picked_x])
        y_train = np.append(y_train, picked_y)
        n_trained += 1
        chosen.append(picked_candidate)

        model = GPSurrogate(seed=seed)
        model.fit(X_train, y_train)

        n_evaluations.append(n_trained)
        r2.append(evaluate_surrogate(model, X_test, y_test).r2)

    return ActiveLearningRun(strategy=strategy, target_name=target_name, n_evaluations=n_evaluations, r2=r2, chosen_candidates=chosen)


def compare_strategies(
    design_space: DesignSpace,
    target_index: int,
    target_name: str,
    n_initial: int,
    n_pool: int,
    n_test: int,
    n_iterations: int,
    seed: int = 1,
    context: PlatformContext = PlatformContext(),
) -> Tuple[ActiveLearningRun, ActiveLearningRun]:
    """Same initial set, pool, and held-out test set for both strategies -- sampled
    from disjoint-in-practice seed offsets (continuous LHS draws essentially never
    collide) -- so the comparison isolates the selection strategy's effect.
    """
    initial_candidates = sample_candidates(design_space, n_initial, seed=seed)
    pool_candidates = sample_candidates(design_space, n_pool, seed=seed + 1000)
    test_candidates = sample_candidates(design_space, n_test, seed=seed + 2000)

    uncertainty_run = run_pool_based_learning(
        design_space, target_index, target_name, "uncertainty",
        initial_candidates, pool_candidates, test_candidates, n_iterations, seed, context,
    )
    random_run = run_pool_based_learning(
        design_space, target_index, target_name, "random",
        initial_candidates, pool_candidates, test_candidates, n_iterations, seed, context,
    )
    return uncertainty_run, random_run
