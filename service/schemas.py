"""Pydantic request/response models for the scientific service's HTTP API."""

from typing import Dict, List

from pydantic import BaseModel, Field, field_validator

from apex.design.components import BATTERY_CHEMISTRIES, MOTOR_ARCHITECTURES, TIRE_CHOICES

_NUM_MOTORS_CHOICES = {"1", "2"}


class CandidateSpec(BaseModel):
    battery_capacity_kwh: float = Field(gt=0)
    motor_power_kw: float = Field(gt=0)
    gear_ratio: float = Field(gt=0)
    drag_coefficient: float = Field(ge=0)
    frontal_area_m2: float = Field(gt=0)
    motor_architecture: str
    battery_chemistry: str
    num_motors: str
    tire_choice: str

    @field_validator("motor_architecture")
    @classmethod
    def _check_motor_architecture(cls, v: str) -> str:
        if v not in MOTOR_ARCHITECTURES:
            raise ValueError(f"motor_architecture must be one of {sorted(MOTOR_ARCHITECTURES)}, got {v!r}")
        return v

    @field_validator("battery_chemistry")
    @classmethod
    def _check_battery_chemistry(cls, v: str) -> str:
        if v not in BATTERY_CHEMISTRIES:
            raise ValueError(f"battery_chemistry must be one of {sorted(BATTERY_CHEMISTRIES)}, got {v!r}")
        return v

    @field_validator("tire_choice")
    @classmethod
    def _check_tire_choice(cls, v: str) -> str:
        if v not in TIRE_CHOICES:
            raise ValueError(f"tire_choice must be one of {sorted(TIRE_CHOICES)}, got {v!r}")
        return v

    @field_validator("num_motors")
    @classmethod
    def _check_num_motors(cls, v: str) -> str:
        if v not in _NUM_MOTORS_CHOICES:
            raise ValueError(f"num_motors must be one of {sorted(_NUM_MOTORS_CHOICES)}, got {v!r}")
        return v


class CostBreakdown(BaseModel):
    glider_usd: float
    battery_usd: float
    motor_usd: float
    tire_delta_usd: float
    total_usd: float


class MassBreakdown(BaseModel):
    glider_kg: float
    battery_kg: float
    motor_kg: float
    tire_delta_kg: float
    total_kg: float


class EvaluateResponse(BaseModel):
    vehicle_name: str
    mass_kg: float
    manufacturing_cost_usd: float
    zero_to_sixty_s: float
    range_mi: float
    cost_breakdown: CostBreakdown
    mass_breakdown: MassBreakdown


class RequirementSpec(BaseModel):
    kind: str
    threshold: float


class MissionSpec(BaseModel):
    name: str = "custom mission"
    requirements: List[RequirementSpec]


class ParetoRequest(BaseModel):
    mission: MissionSpec
    pop_size: int = Field(default=40, ge=4, le=400)
    n_gen: int = Field(default=15, ge=1, le=200)
    seed: int = 1


class RobustCheckRequest(BaseModel):
    candidate: CandidateSpec
    requirements: List[RequirementSpec]
    n_samples: int = Field(default=200, ge=10, le=2000)
    seed: int = 1


class RobustRequirementResultResponse(BaseModel):
    name: str
    unit: str
    threshold: float
    reliability_target: float
    fraction_satisfied: float
    satisfied: bool
    nominal_value: float
    worst_value: float


class RobustCheckResponse(BaseModel):
    robustly_feasible: bool
    n_samples: int
    requirements: List[RobustRequirementResultResponse]


class ParetoPointResponse(BaseModel):
    candidate: CandidateSpec
    objective_values: Dict[str, float]


class ParetoResponse(BaseModel):
    n_points: int
    points: List[ParetoPointResponse]


class ContinuousVariableSpec(BaseModel):
    name: str
    lower: float
    upper: float
    unit: str


class DiscreteVariableSpec(BaseModel):
    name: str
    choices: List[str]


class DesignSpaceResponse(BaseModel):
    continuous: List[ContinuousVariableSpec]
    discrete: List[DiscreteVariableSpec]


class BenchmarkVehicleResponse(BaseModel):
    name: str
    epa_range_mi: float
    msrp_usd: float
    vehicle_type: str
    drivetrain: str


class AgentChatRequest(BaseModel):
    # Single-turn only: each call is a fresh agent run with no prior history.
    # Multi-turn conversation persistence needs a server-side session store
    # (round-tripping raw Anthropic SDK content blocks through JSON on the wire
    # is more machinery than this phase's scope justifies) -- a known next step,
    # not built here. See agent/README.md.
    message: str = Field(min_length=1)


class AgentToolCallSummary(BaseModel):
    name: str
    input: dict
    result: dict
    is_error: bool


class AgentChatResponse(BaseModel):
    final_text: str
    tool_calls: List[AgentToolCallSummary]
    hops_used: int
    forced_final: bool

class RobustSelectRequest(BaseModel):
    candidates: List[CandidateSpec] = Field(min_length=1, max_length=50)
    requirements: List[RequirementSpec] = Field(min_length=1, max_length=10)
    n_samples: int = Field(default=300, ge=10, le=3000)
    seed: int = 2026
    cvar_alpha: float = Field(default=0.90, gt=0.0, lt=1.0)
