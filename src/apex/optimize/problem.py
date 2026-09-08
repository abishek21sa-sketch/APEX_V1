"""Wraps a Phase 3 DesignSpace + Mission into a pymoo mixed-variable multi-objective
Problem. pymoo's Real/Choice variable types map directly onto Phase 3's
ContinuousVariable/DiscreteVariable, and a Mission's Requirements become the
Problem's inequality constraints -- there's exactly one representation of "what's
optimizable" and "what's feasible" in this codebase, reused here rather than
duplicated in optimizer-specific form.
"""

import dataclasses
from typing import List

from pymoo.core.problem import ElementwiseProblem
from pymoo.core.variable import Choice, Real

from ..design import DesignCandidate, Mission, PlatformContext, build_vehicle
from ..design.variables import DesignSpace
from .objectives import Objective


class ArchitectureProblem(ElementwiseProblem):
    def __init__(
        self,
        design_space: DesignSpace,
        mission: Mission,
        objectives: List[Objective],
        context: PlatformContext = PlatformContext(),
    ):
        candidate_fields = {f.name for f in dataclasses.fields(DesignCandidate)}
        space_fields = {v.name for v in design_space.variables}
        if candidate_fields != space_fields:
            raise ValueError(
                "design_space variables must exactly match DesignCandidate's fields; "
                f"got {sorted(space_fields)}, expected {sorted(candidate_fields)}"
            )
        if not objectives:
            raise ValueError("objectives must be non-empty")

        self.design_space = design_space
        self.mission = mission
        self.objectives = objectives
        self.context = context

        pymoo_vars = {}
        for v in design_space.continuous:
            pymoo_vars[v.name] = Real(bounds=(v.lower, v.upper))
        for v in design_space.discrete:
            pymoo_vars[v.name] = Choice(options=list(v.choices))

        super().__init__(vars=pymoo_vars, n_obj=len(objectives), n_ieq_constr=len(mission.requirements))

    def to_candidate(self, x: dict) -> DesignCandidate:
        return DesignCandidate(
            **{v.name: float(x[v.name]) for v in self.design_space.continuous},
            **{v.name: str(x[v.name]) for v in self.design_space.discrete},
        )

    def _evaluate(self, X, out, *args, **kwargs) -> None:
        candidate = self.to_candidate(X)
        vehicle, report = build_vehicle(candidate, self.context)

        out["F"] = [obj.signed_value(vehicle, report) for obj in self.objectives]

        if self.mission.requirements:
            results = self.mission.evaluate(vehicle, report)
            # pymoo's inequality-constraint convention is g <= 0 == feasible.
            # Requirement.margin is positive when satisfied (slack) and negative
            # when violated, so -margin lines up with that convention directly.
            out["G"] = [-r.margin for r in results]
