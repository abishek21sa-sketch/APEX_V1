import numpy as np
import pytest

from apex.surrogate import GPSurrogate, RandomForestSurrogate, evaluate_surrogate


def _synthetic_linear_dataset(n=200, seed=1):
    rng = np.random.default_rng(seed)
    X = rng.uniform(-5.0, 5.0, size=(n, 3))
    y = 2.0 * X[:, 0] - 3.0 * X[:, 1] + 0.5 * X[:, 2] + rng.normal(0.0, 0.05, size=n)
    return X, y


@pytest.mark.parametrize("Surrogate", [GPSurrogate, RandomForestSurrogate])
def test_predict_returns_mean_and_std_of_matching_shape(Surrogate):
    X, y = _synthetic_linear_dataset(n=40)
    model = Surrogate()
    model.fit(X, y)
    mean, std = model.predict(X[:5])
    assert mean.shape == (5,)
    assert std.shape == (5,)
    assert np.all(std >= 0.0)


@pytest.mark.parametrize("Surrogate", [GPSurrogate, RandomForestSurrogate])
def test_fits_a_simple_linear_function_accurately(Surrogate):
    X_train, y_train = _synthetic_linear_dataset(n=150, seed=1)
    X_test, y_test = _synthetic_linear_dataset(n=50, seed=2)
    model = Surrogate()
    model.fit(X_train, y_train)
    metrics = evaluate_surrogate(model, X_test, y_test)
    assert metrics.r2 > 0.9  # a near-linear function should be easy for either technique


def test_gp_predictive_std_is_higher_far_from_training_data():
    rng = np.random.default_rng(3)
    X_train = rng.uniform(-1.0, 1.0, size=(30, 2))
    y_train = X_train[:, 0] + X_train[:, 1]
    model = GPSurrogate()
    model.fit(X_train, y_train)

    near = np.array([[0.0, 0.0]])  # inside the training region
    far = np.array([[20.0, 20.0]])  # well outside it
    _, std_near = model.predict(near)
    _, std_far = model.predict(far)
    assert std_far[0] > std_near[0]


def test_random_forest_std_is_zero_when_all_trees_agree_on_a_constant():
    X = np.zeros((20, 2))
    y = np.full(20, 5.0)
    model = RandomForestSurrogate(n_estimators=10)
    model.fit(X, y)
    mean, std = model.predict(np.zeros((1, 2)))
    assert mean[0] == pytest.approx(5.0)
    assert std[0] == pytest.approx(0.0)
