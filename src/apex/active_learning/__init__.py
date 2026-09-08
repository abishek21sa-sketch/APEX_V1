"""Phase 7 of the APEX platform: pool-based active-learning design-space
exploration on top of Phase 6's GP surrogate -- closing the loop the roadmap
describes as "simulate -> learn -> identify uncertainty -> choose experiment ->
simulate -> update model -> optimize."

    loop.py -- run_pool_based_learning(): one uncertainty- or random-selection
               run against a shared candidate pool and held-out test set;
               compare_strategies(): both strategies on identical data, isolating
               the effect of selection strategy on learning-curve accuracy

Phase 6 already showed the GP's predictive uncertainty behaves the way active
learning needs (low near training data, high far from it) -- this phase spends
that signal: instead of Phase 6's uniform Latin Hypercube sampling, each new real
physics evaluation goes to whatever the current surrogate is most unsure about.
"""

from .loop import STRATEGIES, ActiveLearningRun, compare_strategies, run_pool_based_learning, select_next_index

__all__ = [
    "STRATEGIES",
    "ActiveLearningRun",
    "compare_strategies",
    "run_pool_based_learning",
    "select_next_index",
]
