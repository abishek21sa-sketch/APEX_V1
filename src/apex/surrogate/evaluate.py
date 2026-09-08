"""Train/test split plus a per-target GP-vs-RF comparison over a
SimulationDataset -- turns raw (X, Y) into the accuracy numbers a surrogate-vs-
real-physics tradeoff decision actually needs, and hands back fitted models a
caller (e.g. Phase 7's active-learning loop) can reuse for prediction directly.
"""

from dataclasses import dataclass
from typing import List

from sklearn.model_selection import train_test_split

from .dataset import TARGET_NAMES, SimulationDataset
from .models import GPSurrogate, RandomForestSurrogate, SurrogateMetrics, evaluate_surrogate


@dataclass(frozen=True)
class SurrogateComparison:
    target_name: str
    gp_metrics: SurrogateMetrics
    rf_metrics: SurrogateMetrics
    gp_model: GPSurrogate
    rf_model: RandomForestSurrogate


def train_and_compare(dataset: SimulationDataset, test_size: float = 0.2, seed: int = 1) -> List[SurrogateComparison]:
    X_train, X_test, Y_train, Y_test = train_test_split(dataset.X, dataset.Y, test_size=test_size, random_state=seed)

    comparisons = []
    for i, target_name in enumerate(TARGET_NAMES):
        y_train, y_test = Y_train[:, i], Y_test[:, i]

        gp = GPSurrogate(seed=seed)
        gp.fit(X_train, y_train)
        gp_metrics = evaluate_surrogate(gp, X_test, y_test)

        rf = RandomForestSurrogate(seed=seed)
        rf.fit(X_train, y_train)
        rf_metrics = evaluate_surrogate(rf, X_test, y_test)

        comparisons.append(
            SurrogateComparison(target_name=target_name, gp_metrics=gp_metrics, rf_metrics=rf_metrics, gp_model=gp, rf_model=rf)
        )
    return comparisons
