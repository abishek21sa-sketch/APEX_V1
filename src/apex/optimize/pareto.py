"""Runs NSGA2 (pymoo's mixed-variable variant) over an ArchitectureProblem and
returns a structured Pareto-front result -- built vehicles and human-readable
objective values for every non-dominated feasible solution found, not pymoo's
raw X/F arrays. This is Phase 4's actual search: Phase 3 defined what a candidate
*is* and whether it's feasible; nothing before this module picked one intelligently.
"""

from dataclasses import dataclass
from typing import List

from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.mixed import MixedVariableDuplicateElimination, MixedVariableMating, MixedVariableSampling
from pymoo.optimize import minimize as pymoo_minimize

from ..design import Mission, PlatformContext, DesignCandidate, build_vehicle
from ..design.variables import DesignSpace
from ..physics import VehicleParams
from .objectives import Objective
from .problem import ArchitectureProblem


@dataclass(frozen=True)
class ParetoPoint:
    candidate: DesignCandidate
    vehicle: VehicleParams
    objective_values: dict  # {objective.name: raw_value}, natural units/direction


@dataclass(frozen=True)
class ParetoResult:
    points: List[ParetoPoint]
    pop_size: int
    n_generations: int


def run_pareto_search(
    design_space: DesignSpace,
    mission: Mission,
    objectives: List[Objective],
    context: PlatformContext = PlatformContext(),
    pop_size: int = 100,
    n_gen: int = 40,
    seed: int = 1,
) -> ParetoResult:
    """NSGA2 with pymoo's mixed-variable operators, so Phase 3's Choice-type design
    variables (motor architecture, battery chemistry, tire choice, num_motors) are
    searched natively alongside the continuous ones -- not one-hot-encoded or
    otherwise smuggled into a continuous relaxation.
    """
    problem = ArchitectureProblem(design_space, mission, objectives, context)
    algorithm = NSGA2(
        pop_size=pop_size,
        sampling=MixedVariableSampling(),
        mating=MixedVariableMating(eliminate_duplicates=MixedVariableDuplicateElimination()),
        eliminate_duplicates=MixedVariableDuplicateElimination(),
    )
    result = pymoo_minimize(problem, algorithm, ("n_gen", n_gen), seed=seed, verbose=False)

    points = []
    if result.X is not None:
        for x in result.X:
            candidate = problem.to_candidate(x)
            vehicle, report = build_vehicle(candidate, context)
            objective_values = {obj.name: obj.raw_value(vehicle, report) for obj in objectives}
            points.append(ParetoPoint(candidate=candidate, vehicle=vehicle, objective_values=objective_values))

    return ParetoResult(points=points, pop_size=pop_size, n_generations=n_gen)
