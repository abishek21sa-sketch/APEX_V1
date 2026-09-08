import csv
from pathlib import Path

import numpy as np
import pytest

from apex.design import build_vehicle, default_design_space
from apex.physics import constant_speed_range_km, zero_to_sixty_s
from apex.physics.constants import MPH_TO_MPS
from apex.surrogate import TARGET_NAMES, feature_names, generate_dataset


def test_generate_dataset_shapes_match_requested_size():
    space = default_design_space()
    dataset = generate_dataset(space, n_samples=40, seed=1)
    assert len(dataset.candidates) == 40
    assert dataset.X.shape == (40, len(feature_names(space)))
    assert dataset.Y.shape == (40, len(TARGET_NAMES))


def test_generate_dataset_is_reproducible_with_a_fixed_seed():
    space = default_design_space()
    d1 = generate_dataset(space, n_samples=20, seed=5)
    d2 = generate_dataset(space, n_samples=20, seed=5)
    assert np.array_equal(d1.X, d2.X)
    assert np.array_equal(d1.Y, d2.Y)
    assert d1.candidates == d2.candidates


def test_continuous_samples_cover_the_declared_ranges_well():
    # Latin Hypercube Sampling should spread samples across each continuous
    # dimension's full range, not cluster in a corner -- a basic space-filling
    # sanity check (not testing LHS's internal algorithm, just that scaling and
    # wiring into candidates didn't collapse the range).
    space = default_design_space()
    dataset = generate_dataset(space, n_samples=60, seed=2)
    battery_values = [c.battery_capacity_kwh for c in dataset.candidates]
    lower, upper = space["battery_capacity_kwh"].lower, space["battery_capacity_kwh"].upper
    span = upper - lower
    assert min(battery_values) < lower + 0.15 * span
    assert max(battery_values) > upper - 0.15 * span


def test_discrete_combinations_are_evenly_covered_not_left_to_chance():
    space = default_design_space()
    n_combos = 1
    for v in space.discrete:
        n_combos *= len(v.choices)
    dataset = generate_dataset(space, n_samples=n_combos * 6, seed=3)
    architectures = [c.motor_architecture for c in dataset.candidates]
    counts = {a: architectures.count(a) for a in set(architectures)}
    # Each of the 3 architectures should appear a comparable number of times, not
    # e.g. one dominating because of unlucky random discrete assignment.
    assert max(counts.values()) - min(counts.values()) <= 2


def test_targets_match_a_direct_physics_evaluation_for_a_spot_checked_sample():
    # Catches encoding/column-alignment bugs: dataset targets must equal what
    # calling the physics kernel directly on that same candidate produces.
    space = default_design_space()
    dataset = generate_dataset(space, n_samples=15, seed=4)
    i = 3
    vehicle, report = build_vehicle(dataset.candidates[i])
    assert dataset.Y[i, 0] == pytest.approx(report.total_manufacturing_cost)
    assert dataset.Y[i, 1] == pytest.approx(vehicle.mass_kg)
    assert dataset.Y[i, 2] == pytest.approx(zero_to_sixty_s(vehicle))
    assert dataset.Y[i, 3] == pytest.approx(constant_speed_range_km(vehicle, 65.0 * MPH_TO_MPS) * 0.621371)


def test_save_csv_round_trips_header_and_row_count(tmp_path):
    space = default_design_space()
    dataset = generate_dataset(space, n_samples=10, seed=6)
    out_path = tmp_path / "dataset.csv"
    dataset.save_csv(out_path)

    with Path(out_path).open(newline="") as f:
        rows = list(csv.reader(f))
    header, data_rows = rows[0], rows[1:]
    assert header == feature_names(space) + TARGET_NAMES
    assert len(data_rows) == 10
    assert len(data_rows[0]) == len(header)
