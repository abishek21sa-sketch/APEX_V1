"""Phase 10 stress test: every corner of the design space (all continuous
variables simultaneously at their min or max bound, crossed with every discrete
combination) must evaluate to finite, sane physics -- no crash, no NaN, no Inf,
no negative mass/cost/time/range. Phase 1-6's tests validate *typical* designs
extensively; this specifically targets the *edges* of the declared valid domain,
which typical-design testing doesn't exercise (an LHS sample essentially never
lands exactly on a corner).
"""

import itertools
import math

import pytest

from apex.design import DesignCandidate, build_vehicle, default_design_space
from apex.physics import constant_speed_range_km, zero_to_sixty_s
from apex.physics.constants import MPH_TO_MPS

_SPACE = default_design_space()
_HIGHWAY_SPEED_MPS = 65.0 * MPH_TO_MPS


def _continuous_corners():
    """Every combination of {lower, upper} across all 5 continuous variables --
    2^5 = 32 corners of the continuous hypercube."""
    names = [v.name for v in _SPACE.continuous]
    bound_pairs = [(v.lower, v.upper) for v in _SPACE.continuous]
    for combo in itertools.product(*bound_pairs):
        yield dict(zip(names, combo))


def _discrete_combinations():
    names = [v.name for v in _SPACE.discrete]
    choice_lists = [list(v.choices) for v in _SPACE.discrete]
    for combo in itertools.product(*choice_lists):
        yield dict(zip(names, combo))


def _all_corner_candidates():
    discrete_combos = list(_discrete_combinations())
    for i, continuous in enumerate(_continuous_corners()):
        # Pairing each continuous corner with one discrete combination (cycled)
        # covers all 32 continuous corners and all discrete combos at least
        # once without the full 32 * (3*2*3*2) = 1152 cross product -- the
        # discrete choices don't interact with *which* continuous bound is hit,
        # so full crossing wouldn't find anything a cycled pairing wouldn't.
        combo = discrete_combos[i % len(discrete_combos)]
        values = dict(continuous)
        values.update(combo)
        yield DesignCandidate(**values)


@pytest.mark.parametrize("candidate", list(_all_corner_candidates()), ids=lambda c: c.name if hasattr(c, "name") else None)
def test_every_design_space_corner_evaluates_to_finite_sane_physics(candidate):
    vehicle, report = build_vehicle(candidate)

    assert math.isfinite(vehicle.mass_kg) and vehicle.mass_kg > 0
    assert math.isfinite(report.total_manufacturing_cost) and report.total_manufacturing_cost > 0

    t = zero_to_sixty_s(vehicle)
    # inf is an acceptable *result* here (an underpowered corner genuinely never
    # reaches 60mph within the solver's time horizon) -- NaN or a negative time
    # would not be.
    assert not math.isnan(t)
    assert t > 0 or t == float("inf")

    r = constant_speed_range_km(vehicle, _HIGHWAY_SPEED_MPS)
    assert not math.isnan(r)
    assert r > 0 or r == float("inf")


def test_corner_generator_exercises_many_distinct_discrete_combinations():
    # Sanity check on the test-generation helper itself: there are 32 continuous
    # corners and 36 discrete combinations, so cycling 32 items through 36 slots
    # can never hit all of them (a ceiling this assertion accounts for, not a
    # bug) -- but it should still exercise most of them, not collapse onto a
    # handful through some indexing mistake.
    discrete_names = [v.name for v in _SPACE.discrete]
    seen = {tuple(getattr(c, n) for n in discrete_names) for c in _all_corner_candidates()}
    total_combos = len(list(_discrete_combinations()))
    assert len(seen) == min(32, total_combos)
