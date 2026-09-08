"""The design-space primitives Phase 4's optimizer will search over: bounded
continuous variables and named-choice discrete variables, exactly the MINLP
(mixed-integer nonlinear) mix the platform's architecture calls for -- battery
capacity/gearing/aero are continuous, motor architecture/battery chemistry/tire
choice are discrete engineering decisions, not points on a continuum.

This module only defines the *space*; candidate.py turns one point in it into a
concrete, physically consistent VehicleParams via the mass/cost buildup.
"""

from dataclasses import dataclass
from typing import Sequence, Union


@dataclass(frozen=True)
class ContinuousVariable:
    name: str
    lower: float
    upper: float
    unit: str = ""

    def __post_init__(self) -> None:
        if self.lower >= self.upper:
            raise ValueError(f"{self.name}: lower ({self.lower}) must be < upper ({self.upper})")

    def clip(self, value: float) -> float:
        return min(max(value, self.lower), self.upper)

    def contains(self, value: float) -> bool:
        return self.lower <= value <= self.upper


@dataclass(frozen=True)
class DiscreteVariable:
    name: str
    choices: Sequence[str]

    def __post_init__(self) -> None:
        if len(self.choices) < 1:
            raise ValueError(f"{self.name}: must have at least one choice")
        if len(set(self.choices)) != len(self.choices):
            raise ValueError(f"{self.name}: choices must be unique, got {self.choices}")

    def contains(self, value: str) -> bool:
        return value in self.choices


DesignVariable = Union[ContinuousVariable, DiscreteVariable]


@dataclass(frozen=True)
class DesignSpace:
    """An ordered collection of design variables. Order matters for anything that
    needs a flat vector representation (Phase 4's continuous solvers); discrete
    variables are looked up by name during design-space evaluation regardless.
    """

    variables: Sequence[DesignVariable]

    def __post_init__(self) -> None:
        names = [v.name for v in self.variables]
        if len(set(names)) != len(names):
            raise ValueError(f"design variable names must be unique, got {names}")

    @property
    def continuous(self) -> Sequence[ContinuousVariable]:
        return [v for v in self.variables if isinstance(v, ContinuousVariable)]

    @property
    def discrete(self) -> Sequence[DiscreteVariable]:
        return [v for v in self.variables if isinstance(v, DiscreteVariable)]

    def __getitem__(self, name: str) -> DesignVariable:
        for v in self.variables:
            if v.name == name:
                return v
        raise KeyError(f"no design variable named {name!r}")

    def validate_assignment(self, assignment: dict) -> None:
        """Raise ValueError on the first out-of-bounds/invalid-choice value found.
        assignment: {variable_name: value}, must cover every variable in the space.
        """
        missing = [v.name for v in self.variables if v.name not in assignment]
        if missing:
            raise ValueError(f"assignment missing values for: {missing}")
        for v in self.variables:
            value = assignment[v.name]
            if isinstance(v, ContinuousVariable) and not v.contains(value):
                raise ValueError(f"{v.name}={value} outside bounds [{v.lower}, {v.upper}] {v.unit}")
            if isinstance(v, DiscreteVariable) and not v.contains(value):
                raise ValueError(f"{v.name}={value!r} not among choices {list(v.choices)}")
