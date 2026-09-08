"""APEX multi-objective optimization package.

The scientific core remains importable without the optional `pymoo` runtime so
physics, robustness, service health, and APEX-RDS can still operate. Pareto search
is enabled when the declared `pymoo` dependency is installed; callers receive a
clear runtime error instead of an import-time crash otherwise.
"""
from .objectives import (
    Objective,
    default_objectives,
    maximize_highway_range,
    minimize_manufacturing_cost,
    minimize_mass,
    minimize_zero_to_sixty,
)

_PYMOO_AVAILABLE = True
_PYMOO_IMPORT_ERROR = None
try:
    from .problem import ArchitectureProblem
    from .pareto import ParetoPoint, ParetoResult, run_pareto_search
except ModuleNotFoundError as exc:
    if exc.name != "pymoo" and not str(exc.name).startswith("pymoo."):
        raise
    _PYMOO_AVAILABLE = False
    _PYMOO_IMPORT_ERROR = exc
    ArchitectureProblem = None
    ParetoPoint = None
    ParetoResult = None

    def run_pareto_search(*args, **kwargs):
        raise RuntimeError("pymoo is required for Pareto search; install the declared project dependencies") from _PYMOO_IMPORT_ERROR

__all__ = [
    "Objective", "default_objectives", "maximize_highway_range",
    "minimize_manufacturing_cost", "minimize_mass", "minimize_zero_to_sixty",
    "ArchitectureProblem", "ParetoPoint", "ParetoResult", "run_pareto_search",
]
