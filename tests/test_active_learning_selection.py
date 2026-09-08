import numpy as np
import pytest

from apex.active_learning import select_next_index
from apex.surrogate import GPSurrogate


def test_rejects_unknown_strategy():
    rng = np.random.default_rng(1)
    model = GPSurrogate()
    model.fit(np.array([[0.0], [1.0]]), np.array([0.0, 1.0]))
    with pytest.raises(ValueError):
        select_next_index(model, np.array([[0.5]]), "greedy", rng)


def test_uncertainty_strategy_picks_the_argmax_of_predicted_std():
    rng = np.random.default_rng(1)
    # Train tightly around 0 so points far from it carry visibly higher std.
    X_train = np.array([[-0.1], [0.0], [0.1]])
    y_train = np.array([0.0, 0.0, 0.0])
    model = GPSurrogate()
    model.fit(X_train, y_train)

    remaining_X = np.array([[0.05], [50.0], [-0.05]])  # index 1 is far outside training data
    pick = select_next_index(model, remaining_X, "uncertainty", rng)
    _, std = model.predict(remaining_X)
    assert pick == int(np.argmax(std))
    assert pick == 1


def test_random_strategy_stays_within_bounds_and_is_reproducible_with_seeded_rng():
    remaining_X = np.zeros((10, 2))
    model = GPSurrogate()
    model.fit(np.array([[0.0, 0.0], [1.0, 1.0]]), np.array([0.0, 1.0]))

    pick1 = select_next_index(model, remaining_X, "random", np.random.default_rng(7))
    pick2 = select_next_index(model, remaining_X, "random", np.random.default_rng(7))
    assert pick1 == pick2
    assert 0 <= pick1 < 10


def test_random_strategy_ignores_the_model_entirely():
    # Same rng seed, wildly different (even nonsensical) model state -- random
    # selection shouldn't depend on model predictions at all.
    remaining_X = np.zeros((10, 2))
    model_a = GPSurrogate()
    model_a.fit(np.array([[0.0, 0.0], [1.0, 1.0]]), np.array([0.0, 1.0]))
    model_b = GPSurrogate()
    model_b.fit(np.array([[0.0, 0.0], [1.0, 1.0]]), np.array([100.0, -100.0]))

    pick_a = select_next_index(model_a, remaining_X, "random", np.random.default_rng(3))
    pick_b = select_next_index(model_b, remaining_X, "random", np.random.default_rng(3))
    assert pick_a == pick_b
