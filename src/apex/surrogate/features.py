"""Encodes a DesignCandidate as a flat numeric feature vector for scikit-learn
surrogate models: continuous variables pass through as-is, num_motors (an
inherently ordered count, "1"/"2") is cast to a plain numeric feature, and the
genuinely categorical/unordered discrete variables (motor_architecture,
battery_chemistry, tire_choice) are one-hot encoded. Derived from a DesignSpace's
own variable list rather than a hardcoded field order, so it works for any
DesignSpace matching DesignCandidate's fields, not just default_design_space().
"""

from typing import List

import numpy as np

from ..design.candidate import DesignCandidate
from ..design.variables import DesignSpace

# Discrete variables that represent an ordered count, not an unordered category --
# encoded as a plain number rather than one-hot. Domain knowledge that can't be
# derived from DiscreteVariable alone (it doesn't carry an "is_ordinal" flag).
_ORDINAL_DISCRETE_FIELDS = {"num_motors"}


def feature_names(design_space: DesignSpace) -> List[str]:
    names = [v.name for v in design_space.continuous]
    for v in design_space.discrete:
        if v.name in _ORDINAL_DISCRETE_FIELDS:
            names.append(v.name)
        else:
            names.extend(f"{v.name}={c}" for c in v.choices)
    return names


def encode_candidate(candidate: DesignCandidate, design_space: DesignSpace) -> np.ndarray:
    values = [float(getattr(candidate, v.name)) for v in design_space.continuous]
    for v in design_space.discrete:
        actual = getattr(candidate, v.name)
        if v.name in _ORDINAL_DISCRETE_FIELDS:
            values.append(float(actual))
        else:
            values.extend(1.0 if c == actual else 0.0 for c in v.choices)
    return np.array(values, dtype=float)


def encode_candidates(candidates: List[DesignCandidate], design_space: DesignSpace) -> np.ndarray:
    return np.array([encode_candidate(c, design_space) for c in candidates])
