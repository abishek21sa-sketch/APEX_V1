"""Test dependency boundaries for APEX.

The core physics/robustness/service suite must remain runnable when optional runtime
integrations are absent. Tests that exercise NSGA-II are skipped only when `pymoo`
is unavailable; the Windows full acceptance installs the declared base dependency,
so those tests execute there rather than being permanently excluded.
"""
from __future__ import annotations
import importlib.util
import pytest

_PYMOO_AVAILABLE = importlib.util.find_spec("pymoo") is not None
_PYMOO_MODULES = {"test_optimize_pareto.py", "test_optimize_problem.py"}
_PYMOO_NODE_SUFFIXES = {
    "test_agent_tools.py::test_run_pareto_search_returns_points_with_expected_shape",
    "test_agent_tools.py::test_every_tool_result_is_json_serializable",
    "test_service.py::test_pareto_returns_points_matching_requested_mission",
    "test_service.py::test_pareto_with_impossible_mission_returns_zero_points",
}


def pytest_collection_modifyitems(config, items):
    if _PYMOO_AVAILABLE:
        return
    marker=pytest.mark.skip(reason="pymoo dependency is not installed; exercised by Windows full acceptance")
    for item in items:
        basename=item.path.name
        if basename in _PYMOO_MODULES or any(item.nodeid.endswith(suffix) for suffix in _PYMOO_NODE_SUFFIXES):
            item.add_marker(marker)
