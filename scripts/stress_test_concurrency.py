"""Phase 10 stress test: concurrency safety of the Rust backend's in-memory job
store (Arc<Mutex<HashMap>>). Fires several Pareto search jobs at once, each with
a *distinct* mission, then verifies not just that all jobs complete without
crashing, but that each job's result actually satisfies its own mission and not
a neighbor's -- the real risk with a shared job store under concurrent access
isn't a crash, it's silent cross-contamination (job A's result written under
job B's ID), which "did it not crash" alone wouldn't catch.

Requires the Python service (:8001) and Rust backend (:8080) already running:

    uvicorn service.main:app --port 8001          (terminal 1)
    cd backend && cargo run                        (terminal 2)
    python scripts/stress_test_concurrency.py       (terminal 3)
"""

import concurrent.futures as cf
import sys
import time

import httpx

BASE = "http://127.0.0.1:8080/api"
THRESHOLDS = [4.0, 5.0, 6.0, 7.0, 8.0, 9.0]


def start_job(threshold: float) -> tuple:
    body = {
        "mission": {
            "name": f"concurrent-{threshold}",
            "requirements": [
                {"kind": "max_acceleration_time_s", "threshold": threshold},
                {"kind": "min_highway_range_mi", "threshold": 1.0},
            ],
        },
        "pop_size": 12,
        "n_gen": 3,
        "seed": int(threshold),
    }
    response = httpx.post(f"{BASE}/pareto", json=body, timeout=30)
    response.raise_for_status()
    return threshold, response.json()["job_id"]


def main() -> None:
    try:
        httpx.get(f"{BASE}/health", timeout=3).raise_for_status()
    except httpx.HTTPError as exc:
        print(f"Rust backend not reachable at {BASE} -- start it first (see this script's docstring). ({exc})")
        raise SystemExit(1) from exc

    print(f"Firing {len(THRESHOLDS)} concurrent Pareto jobs with distinct missions...")
    with cf.ThreadPoolExecutor(max_workers=len(THRESHOLDS)) as executor:
        jobs = dict(executor.map(start_job, THRESHOLDS))

    if len(set(jobs.values())) != len(THRESHOLDS):
        print("FAIL: job IDs collided across concurrent requests")
        raise SystemExit(1)
    print(f"  {len(jobs)} distinct job IDs assigned, no collisions.")

    pending = dict(jobs)
    results = {}
    errors = {}
    t0 = time.time()
    while pending and time.time() - t0 < 90:
        for threshold, job_id in list(pending.items()):
            body = httpx.get(f"{BASE}/pareto/{job_id}", timeout=10).json()
            if body["status"] == "done":
                results[threshold] = body["result"]
                del pending[threshold]
            elif body["status"] == "error":
                errors[threshold] = body["message"]
                del pending[threshold]
        if pending:
            time.sleep(1)

    if pending:
        print(f"FAIL: {len(pending)} job(s) never completed within the timeout")
        raise SystemExit(1)
    if errors:
        print(f"FAIL: {len(errors)} job(s) errored: {errors}")
        raise SystemExit(1)

    print(f"  All {len(results)} jobs settled in {time.time() - t0:.1f}s.\n")

    contaminated = []
    for threshold, result in sorted(results.items()):
        accels = [p["objective_values"]["0-60 mph time"] for p in result["points"]]
        max_accel = max(accels) if accels else None
        print(f"  threshold={threshold}: n_points={result['n_points']}, max 0-60 among its points={max_accel}")
        if any(a > threshold + 1e-6 for a in accels):
            contaminated.append(threshold)

    if contaminated:
        print(f"\nFAIL: job(s) for threshold(s) {contaminated} contain points violating their OWN mission "
              f"-- likely cross-contamination in the shared job store.")
        raise SystemExit(1)

    print("\nPASS: every job's result satisfies its own mission -- no cross-job contamination under concurrency.")


if __name__ == "__main__":
    main()
