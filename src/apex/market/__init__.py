"""Real-world market data, kept separate from the design-space/optimization
modules: this package holds facts about vehicles that actually exist and ship,
not anything this platform simulates or generates.
"""

from .benchmark_vehicles import BENCHMARK_VEHICLES, BenchmarkVehicle

__all__ = ["BENCHMARK_VEHICLES", "BenchmarkVehicle"]
