"""Surrogate models: fit against a SimulationDataset's (X, Y), then predict
(mean, std) for new candidates without touching the physics kernel. Two
techniques, per the platform proposal's own list -- Gaussian Process Regression
(analytic predictive uncertainty, the natural fit for Phase 7's active learning:
"the AI selects the next most informative vehicle architecture to simulate" needs
exactly this) and Random Forest (handles the mixed continuous/one-hot-discrete
feature space natively, no kernel design needed, ensemble spread as a cheaper but
less principled uncertainty proxy) -- fit and compared per target in evaluate.py
rather than picking one technique blindly.
"""

import warnings
from dataclasses import dataclass
from typing import Tuple

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class SurrogateMetrics:
    r2: float
    rmse: float
    mae: float


class GPSurrogate:
    """Gaussian Process Regression with an RBF kernel over standardized features
    and target -- gives an analytic predictive standard deviation per prediction.
    """

    def __init__(self, seed: int = 1):
        self._x_scaler = StandardScaler()
        self._y_mean = 0.0
        self._y_std = 1.0
        kernel = ConstantKernel(1.0, (1e-2, 1e3)) * RBF(length_scale=1.0, length_scale_bounds=(1e-2, 1e3)) + WhiteKernel(
            noise_level=1e-3, noise_level_bounds=(1e-8, 1e0)
        )
        self._model = GaussianProcessRegressor(kernel=kernel, normalize_y=False, n_restarts_optimizer=3, random_state=seed)

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        Xs = self._x_scaler.fit_transform(X)
        self._y_mean = float(np.mean(y))
        self._y_std = float(np.std(y)) or 1.0
        # The L-BFGS kernel-hyperparameter search often lands near a box constraint
        # without fully converging on data this well-fit (near-zero residual noise
        # to explain) -- benign here (predictions are still accurate; see
        # evaluate_surrogate's R2/RMSE), so suppressed rather than left to print a
        # warning on every fit call regardless of whether it matters for the result.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=ConvergenceWarning)
            self._model.fit(Xs, (y - self._y_mean) / self._y_std)

    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        Xs = self._x_scaler.transform(X)
        mean_s, std_s = self._model.predict(Xs, return_std=True)
        return mean_s * self._y_std + self._y_mean, std_s * self._y_std


class RandomForestSurrogate:
    """Random Forest Regression -- handles the mixed continuous/one-hot-discrete
    feature space natively (no scaling or kernel design needed), with the spread
    across trees used as an uncertainty proxy. Less principled than a GP's
    (it's not a calibrated predictive distribution), but real, useful, and far
    cheaper to fit as a training set grows.
    """

    def __init__(self, n_estimators: int = 200, seed: int = 1):
        self._model = RandomForestRegressor(n_estimators=n_estimators, random_state=seed)

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self._model.fit(X, y)

    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        per_tree = np.stack([tree.predict(X) for tree in self._model.estimators_], axis=0)
        return per_tree.mean(axis=0), per_tree.std(axis=0)


def evaluate_surrogate(model, X_test: np.ndarray, y_test: np.ndarray) -> SurrogateMetrics:
    mean, _ = model.predict(X_test)
    return SurrogateMetrics(
        r2=float(r2_score(y_test, mean)),
        rmse=float(root_mean_squared_error(y_test, mean)),
        mae=float(mean_absolute_error(y_test, mean)),
    )
