"""Phase 6 of the APEX platform: a real simulation dataset (Latin Hypercube
Sampling + evenly-cycled discrete combinations, each point evaluated with the
actual Phase 1-4 physics kernel) and surrogate models trained against it, so
design-space exploration doesn't have to pay the full physics-evaluation cost
for every candidate.

    features.py -- encode_candidate()/feature_names(): DesignCandidate <-> a flat
                   numeric feature vector (continuous as-is, ordinal discretes as
                   numbers, categorical discretes one-hot)
    dataset.py  -- generate_dataset(): the LHS+discrete-crossed design of
                   experiments, evaluated against real physics; SimulationDataset
    models.py   -- GPSurrogate/RandomForestSurrogate: fit(X,y) / predict(X) ->
                   (mean, std), two techniques per the platform proposal's list
    evaluate.py -- train_and_compare(): train/test split + per-target GP-vs-RF
                   accuracy comparison, returning fitted models a caller can reuse

Phase 7 (active learning) is the reason GPSurrogate exists at all here rather than
just picking whichever technique scores best on this phase's fixed dataset: its
analytic predictive std is what lets a future sampling loop choose the next
design to actually simulate by uncertainty, not at random.
"""

from .dataset import TARGET_NAMES, SimulationDataset, evaluate_candidates, generate_dataset, sample_candidates
from .evaluate import SurrogateComparison, train_and_compare
from .features import encode_candidate, encode_candidates, feature_names
from .models import GPSurrogate, RandomForestSurrogate, SurrogateMetrics, evaluate_surrogate

__all__ = [
    "TARGET_NAMES",
    "SimulationDataset",
    "evaluate_candidates",
    "generate_dataset",
    "sample_candidates",
    "SurrogateComparison",
    "train_and_compare",
    "encode_candidate",
    "encode_candidates",
    "feature_names",
    "GPSurrogate",
    "RandomForestSurrogate",
    "SurrogateMetrics",
    "evaluate_surrogate",
]
