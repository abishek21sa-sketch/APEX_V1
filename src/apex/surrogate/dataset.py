"""Generates a design-space dataset for surrogate training: Latin Hypercube
Sampling on the continuous sub-space (much better space-filling coverage per
sample than uniform random -- the standard design-of-experiments choice when a
surrogate needs to be accurate everywhere, not just where random sampling
happened to land) crossed with an evenly-cycled sweep of discrete combinations,
so every architecture/chemistry/tire/motor-count combination gets real coverage
rather than being left to chance.

Each sampled candidate is evaluated with the REAL Phase 1-4 physics kernel, not a
surrogate -- this dataset IS the ground truth Phase 6's surrogate models train
against. Targets are the same four objectives Phase 4 optimizes (cost, mass, 0-60
time, range): the well-defined, already-validated quantities this platform can
actually compute, not the full proposal objective list (see optimize/objectives.py).

sample_candidates() and evaluate_candidates() are split out from generate_dataset()
so Phase 7's active-learning loop can reuse the same space-filling sampling for its
candidate pool and the same real-physics evaluation for its on-demand queries,
without duplicating either.
"""

import csv
import itertools
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union

import numpy as np
from scipy.stats import qmc

from .features import encode_candidates, feature_names
from ..design import DesignCandidate, PlatformContext, build_vehicle
from ..design.variables import DesignSpace
from ..physics import constant_speed_range_km, zero_to_sixty_s
from ..physics.constants import MPH_TO_MPS

TARGET_NAMES = ["manufacturing_cost_usd", "mass_kg", "zero_to_sixty_s", "range_mi"]


@dataclass(frozen=True)
class SimulationDataset:
    design_space: DesignSpace
    candidates: List[DesignCandidate]
    X: np.ndarray  # (n, n_features) -- see features.feature_names(design_space)
    Y: np.ndarray  # (n, len(TARGET_NAMES))

    def save_csv(self, path: Union[str, Path]) -> None:
        header = feature_names(self.design_space) + TARGET_NAMES
        with Path(path).open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for x_row, y_row in zip(self.X, self.Y):
                writer.writerow([*x_row, *y_row])


def _evenly_cycled_discrete_combinations(design_space: DesignSpace, n: int, rng: np.random.Generator) -> List[dict]:
    names = [v.name for v in design_space.discrete]
    choice_lists = [list(v.choices) for v in design_space.discrete]
    all_combos = [dict(zip(names, combo)) for combo in itertools.product(*choice_lists)]
    cycled = list(itertools.islice(itertools.cycle(all_combos), n))
    order = rng.permutation(len(cycled))
    return [cycled[i] for i in order]


def sample_candidates(design_space: DesignSpace, n: int, seed: int) -> List[DesignCandidate]:
    """LHS-on-continuous + evenly-cycled-discrete design of experiments -- no
    physics evaluation, just the space-filling sample of *which* designs to
    consider. Different seeds give disjoint-in-practice samples (continuous LHS
    draws essentially never collide), which is what lets an initial training set,
    an active-learning candidate pool, and a held-out test set be sampled
    independently without deliberate index bookkeeping.
    """
    continuous_vars = design_space.continuous
    sampler = qmc.LatinHypercube(d=len(continuous_vars), seed=seed)
    unit_samples = sampler.random(n=n)
    lower = [v.lower for v in continuous_vars]
    upper = [v.upper for v in continuous_vars]
    continuous_samples = qmc.scale(unit_samples, lower, upper)

    rng = np.random.default_rng(seed)
    discrete_combos = _evenly_cycled_discrete_combinations(design_space, n, rng)

    candidates = []
    for continuous_values, combo in zip(continuous_samples, discrete_combos):
        values = {v.name: float(x) for v, x in zip(continuous_vars, continuous_values)}
        values.update(combo)
        candidates.append(DesignCandidate(**values))
    return candidates


def evaluate_candidates(
    candidates: List[DesignCandidate],
    context: PlatformContext = PlatformContext(),
    highway_speed_mps: float = 65.0 * MPH_TO_MPS,
) -> np.ndarray:
    """Real Phase 1-4 physics evaluation -- the expensive ground truth every
    surrogate in this platform ultimately trains against or is checked by.
    """
    Y = np.empty((len(candidates), len(TARGET_NAMES)))
    for i, candidate in enumerate(candidates):
        vehicle, report = build_vehicle(candidate, context)
        Y[i, 0] = report.total_manufacturing_cost
        Y[i, 1] = vehicle.mass_kg
        Y[i, 2] = zero_to_sixty_s(vehicle)
        Y[i, 3] = constant_speed_range_km(vehicle, highway_speed_mps) * 0.621371
    return Y


def generate_dataset(
    design_space: DesignSpace,
    n_samples: int,
    context: PlatformContext = PlatformContext(),
    seed: int = 1,
    highway_speed_mps: float = 65.0 * MPH_TO_MPS,
) -> SimulationDataset:
    candidates = sample_candidates(design_space, n_samples, seed)
    X = encode_candidates(candidates, design_space)
    Y = evaluate_candidates(candidates, context, highway_speed_mps)
    return SimulationDataset(design_space=design_space, candidates=candidates, X=X, Y=Y)
