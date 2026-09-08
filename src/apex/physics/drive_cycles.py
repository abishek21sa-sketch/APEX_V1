"""Speed-vs-time profiles for feeding into energy.simulate_drive_cycle().

The urban/highway cycles here are synthetic — built from accel/cruise/brake/idle
segments tuned to roughly EPA UDDS- and HWFET-like average speeds and character
(stop-and-go city vs. steady highway). They are NOT reproductions of the official
government drive-cycle traces (those are specific published second-by-second
speed tables); do not treat range figures derived from them as EPA-equivalent.
Swap in a real imported trace here once one is available — simulate_drive_cycle()
only needs (t_s, v_mps) arrays, it doesn't care where they came from.
"""

from typing import List, Tuple

import numpy as np

from .constants import MPH_TO_MPS


def _build_cycle(segments: List[Tuple[float, float, float]], dt: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
    """segments: list of (duration_s, v_start_mps, v_end_mps), linearly interpolated."""
    t_chunks, v_chunks = [], []
    t0 = 0.0
    for duration, v_start, v_end in segments:
        n = max(1, int(round(duration / dt)))
        t_chunks.append(t0 + np.arange(n) * dt)
        v_chunks.append(np.linspace(v_start, v_end, n, endpoint=False))
        t0 += n * dt
    t_chunks.append(np.array([t0]))
    v_chunks.append(np.array([segments[-1][2]]))
    return np.concatenate(t_chunks), np.concatenate(v_chunks)


def constant_speed_cycle(speed_mps: float, duration_s: float = 3600.0, dt: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
    t = np.arange(0.0, duration_s + dt, dt)
    v = np.full_like(t, speed_mps)
    return t, v


def synthetic_urban_cycle(n_repeats: int = 8, dt: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
    """Stop-and-go city block: accel to ~30 mph, brief cruise, brake to a stop, idle.
    Average speed lands around 15-20 mph, in the neighborhood of UDDS's ~19.6 mph.
    """
    cruise = 30.0 * MPH_TO_MPS
    block = [
        (12.0, 0.0, cruise),   # accelerate away from a stop
        (15.0, cruise, cruise),  # cruise
        (8.0, cruise, 0.0),    # brake to a stop
        (10.0, 0.0, 0.0),      # idle at the light
    ]
    return _build_cycle(block * n_repeats, dt=dt)


def synthetic_highway_cycle(n_repeats: int = 4, dt: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
    """Steady highway cruise with mild speed variation, average ~48 mph, in the
    neighborhood of HWFET's ~48.3 mph average.
    """
    v_lo, v_hi = 45.0 * MPH_TO_MPS, 55.0 * MPH_TO_MPS
    block = [
        (20.0, v_lo, v_hi),
        (60.0, v_hi, v_hi),
        (20.0, v_hi, v_lo),
        (60.0, v_lo, v_lo),
    ]
    return _build_cycle(block * n_repeats, dt=dt)
