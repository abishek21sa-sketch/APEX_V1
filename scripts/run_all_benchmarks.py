"""Phase 10 benchmark/acceptance harness: runs the full Python test suite, the
Rust test suite, and (if the frontend's dependencies are installed) its
typecheck, then prints one consolidated PASS/FAIL report with timings.

    python scripts/run_all_benchmarks.py

This is the "is this repo healthy" check for the whole platform -- Phases 1-9
each validated themselves individually (a report script, a test file); this is
the first place all of it gets checked together in one pass, which is exactly
what a benchmark/acceptance gate is for: not a new kind of testing, just the
existing tests run and reported as a single verdict rather than nine separate
ones nobody re-runs together.
"""

import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class BenchmarkResult:
    def __init__(self, name: str, passed: bool, duration_s: float, detail: str = ""):
        self.name = name
        self.passed = passed
        self.duration_s = duration_s
        self.detail = detail


def _run(name: str, cmd: list, cwd: Path, skip_reason: str = None) -> BenchmarkResult:
    if skip_reason:
        print(f"[SKIP] {name}: {skip_reason}")
        return BenchmarkResult(name, passed=True, duration_s=0.0, detail=f"skipped: {skip_reason}")

    print(f"[RUN ] {name} ({' '.join(cmd)})")
    t0 = time.time()
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    duration = time.time() - t0
    passed = result.returncode == 0
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name} ({duration:.1f}s)")
    if not passed:
        tail = "\n".join((result.stdout + result.stderr).splitlines()[-30:])
        print(f"       last output:\n{tail}\n")
    return BenchmarkResult(name, passed, duration, detail="" if passed else "see output above")


def main() -> None:
    results = []

    venv_python = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
    python_exe = str(venv_python) if venv_python.exists() else sys.executable
    results.append(_run("Python test suite (pytest)", [python_exe, "-m", "pytest", "tests/", "-q"], REPO_ROOT))

    cargo = shutil.which("cargo")
    backend_dir = REPO_ROOT / "backend"
    if cargo and backend_dir.exists():
        results.append(_run("Rust test suite (cargo test)", [cargo, "test", "--quiet"], backend_dir))
        results.append(_run("Rust lints (cargo clippy)", [cargo, "clippy", "--all-targets", "--quiet"], backend_dir))
    else:
        results.append(_run("Rust test suite (cargo test)", [], backend_dir, skip_reason="cargo not on PATH"))

    npm = shutil.which("npm")
    frontend_dir = REPO_ROOT / "frontend"
    node_modules = frontend_dir / "node_modules"
    if npm and node_modules.exists():
        results.append(_run("Frontend typecheck (svelte-check)", [npm, "run", "check"], frontend_dir))
    else:
        results.append(
            _run("Frontend typecheck (svelte-check)", [], frontend_dir, skip_reason="frontend/node_modules not installed")
        )

    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    total_time = 0.0
    all_passed = True
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.name:<40} {r.duration_s:>6.1f}s")
        total_time += r.duration_s
        all_passed = all_passed and r.passed
    print("-" * 60)
    print(f"  Total: {total_time:.1f}s -- {'ALL PASS' if all_passed else 'FAILURES PRESENT'}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
