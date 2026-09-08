"""Tool definitions (Anthropic tool-use JSON schemas) and their dispatch functions
for the Vehicle Systems Engineer Agent. Per the platform proposal: the agent
"should not directly control optimization" -- it can only affect the world
through these seven tools, each of which calls straight into the real,
already-validated Phase 1-5 kernel/design-space/optimizer/robust-checker. There
is no eighth path where the model just states a number; every claim it makes
about a design has to come from a tool result.

Numeric bounds and discrete choices in the schemas below are read from
apex.design.default_design_space() at import time, not hardcoded, so they can't
silently drift from what build_vehicle() actually accepts.
"""

from typing import Callable, Dict, List

from apex.design import DesignCandidate, PlatformContext, build_vehicle, default_design_space
from apex.design.components import BATTERY_CHEMISTRIES, MOTOR_ARCHITECTURES, TIRE_CHOICES
from apex.optimize import default_objectives, run_pareto_search
from apex.physics import constant_speed_range_km, zero_to_sixty_s
from apex.physics.constants import MPH_TO_MPS
from apex.robust import (
    RobustMission,
    UncertaintyModel,
    robust_max_acceleration_time_s,
    robust_max_braking_distance_m,
    robust_min_highway_range_mi,
)

from service.mission_registry import REQUIREMENT_KINDS, build_mission

_SPACE = default_design_space()
_HIGHWAY_SPEED_MPS = 65.0 * MPH_TO_MPS

_REQUIREMENT_DESCRIPTIONS = {
    "max_acceleration_time_s": "0-60 mph time must be at most this many seconds",
    "min_highway_range_mi": "Highway range at 65mph must be at least this many miles",
    "max_mass_kg": "Curb mass must be at most this many kg",
    "min_gradeability_pct": "Sustained climbable grade at 20 m/s must be at least this percent",
    "max_braking_distance_m": "60-0mph braking distance must be at most this many meters",
    "max_manufacturing_cost_usd": "Manufacturing cost (buildup, not MSRP) must be at most this many USD",
}

# Requirement kinds Phase 5's robust (Monte Carlo) checker actually supports --
# a subset of the full nominal REQUIREMENT_KINDS list, see robust/requirements.py.
_ROBUST_REQUIREMENT_BUILDERS = {
    "max_acceleration_time_s": robust_max_acceleration_time_s,
    "min_highway_range_mi": robust_min_highway_range_mi,
    "max_braking_distance_m": robust_max_braking_distance_m,
}


def _candidate_input_schema() -> dict:
    properties = {}
    for v in _SPACE.continuous:
        properties[v.name] = {
            "type": "number",
            "minimum": v.lower,
            "maximum": v.upper,
            "description": f"{v.name} ({v.unit}), valid range [{v.lower}, {v.upper}]",
        }
    properties["motor_architecture"] = {"type": "string", "enum": sorted(MOTOR_ARCHITECTURES)}
    properties["battery_chemistry"] = {"type": "string", "enum": sorted(BATTERY_CHEMISTRIES)}
    properties["num_motors"] = {"type": "string", "enum": ["1", "2"]}
    properties["tire_choice"] = {"type": "string", "enum": sorted(TIRE_CHOICES)}
    required = [v.name for v in _SPACE.continuous] + ["motor_architecture", "battery_chemistry", "num_motors", "tire_choice"]
    return {"type": "object", "properties": properties, "required": required}


def _requirements_input_schema(kinds: List[str]) -> dict:
    return {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": kinds},
                "threshold": {"type": "number"},
            },
            "required": ["kind", "threshold"],
        },
    }


def _candidate_from_dict(data: dict) -> DesignCandidate:
    return DesignCandidate(**{k: data[k] for k in DesignCandidate.__dataclass_fields__})


def _evaluate_summary(vehicle, report) -> dict:
    return {
        "vehicle_name": vehicle.name,
        "mass_kg": round(vehicle.mass_kg, 1),
        "manufacturing_cost_usd": round(report.total_manufacturing_cost, 2),
        "zero_to_sixty_s": round(zero_to_sixty_s(vehicle), 2),
        "range_mi": round(constant_speed_range_km(vehicle, _HIGHWAY_SPEED_MPS) * 0.621371, 1),
    }


def tool_get_design_space(_input: dict) -> dict:
    return {
        "continuous": [{"name": v.name, "lower": v.lower, "upper": v.upper, "unit": v.unit} for v in _SPACE.continuous],
        "discrete": [{"name": v.name, "choices": list(v.choices)} for v in _SPACE.discrete],
    }


def tool_list_requirement_kinds(_input: dict) -> dict:
    return {
        "kinds": [
            {"kind": k, "description": _REQUIREMENT_DESCRIPTIONS.get(k, ""), "robust_supported": k in _ROBUST_REQUIREMENT_BUILDERS}
            for k in REQUIREMENT_KINDS
        ]
    }


def tool_evaluate_candidate(input: dict) -> dict:
    candidate = _candidate_from_dict(input)
    vehicle, report = build_vehicle(candidate, PlatformContext())
    return _evaluate_summary(vehicle, report)


def tool_check_mission(input: dict) -> dict:
    candidate = _candidate_from_dict(input["candidate"])
    vehicle, report = build_vehicle(candidate, PlatformContext())
    mission = build_mission("agent check", input["requirements"])
    results = mission.evaluate(vehicle, report)
    return {
        "feasible": bool(mission.is_feasible(results)),
        "requirements": [
            {
                "name": r.name,
                # r.satisfied can be numpy.bool_ (from a numpy-typed physics value
                # compared against a threshold) -- the stdlib json module can't
                # serialize that, unlike numpy floats, which happen to subclass
                # Python float. Cast explicitly rather than relying on that quirk.
                "satisfied": bool(r.satisfied),
                "value": round(r.value, 3),
                "threshold": r.threshold,
                "margin": round(r.margin, 3),
            }
            for r in results
        ],
    }


def tool_run_pareto_search(input: dict) -> dict:
    mission = build_mission("agent pareto search", input["requirements"])
    result = run_pareto_search(
        _SPACE,
        mission,
        default_objectives(),
        pop_size=input.get("pop_size", 30),
        n_gen=input.get("n_gen", 10),
        seed=input.get("seed", 1),
    )
    return {
        "n_points": len(result.points),
        "points": [{"candidate": p.candidate.as_dict(), "objective_values": {k: round(v, 2) for k, v in p.objective_values.items()}} for p in result.points],
    }


def tool_sensitivity_analysis(input: dict) -> dict:
    base = input["base_candidate"]
    field = input["field"]
    if field not in DesignCandidate.__dataclass_fields__:
        raise ValueError(f"unknown candidate field {field!r}; expected one of {sorted(DesignCandidate.__dataclass_fields__)}")

    rows = []
    for value in input["values"]:
        varied = dict(base)
        varied[field] = value
        candidate = _candidate_from_dict(varied)
        vehicle, report = build_vehicle(candidate, PlatformContext())
        rows.append({field: value, **_evaluate_summary(vehicle, report)})
    return {"field": field, "results": rows}


def tool_robust_check(input: dict) -> dict:
    candidate = _candidate_from_dict(input["candidate"])
    vehicle, _ = build_vehicle(candidate, PlatformContext())

    requirements = []
    for spec in input["requirements"]:
        kind = spec["kind"]
        if kind not in _ROBUST_REQUIREMENT_BUILDERS:
            raise ValueError(f"kind {kind!r} isn't supported by the robust checker; expected one of {sorted(_ROBUST_REQUIREMENT_BUILDERS)}")
        requirements.append(_ROBUST_REQUIREMENT_BUILDERS[kind](spec["threshold"]))

    mission = RobustMission(name="agent robust check", requirements=requirements, uncertainty_model=UncertaintyModel())
    n_samples = input.get("n_samples", 50)
    results = mission.evaluate(vehicle, n_samples=n_samples, seed=input.get("seed", 1))
    return {
        "robustly_feasible": bool(RobustMission.is_feasible(results)),
        "n_samples": n_samples,
        "requirements": [
            {
                "name": r.name,
                "satisfied": bool(r.satisfied),
                "fraction_satisfied": round(r.fraction_satisfied, 3),
                "reliability_target": r.reliability_target,
                "nominal_value": round(r.nominal_value, 3),
                "worst_value": round(r.worst_value, 3),
                "threshold": r.threshold,
            }
            for r in results
        ],
    }


TOOL_DEFINITIONS: List[dict] = [
    {
        "name": "get_design_space",
        "description": "Get the valid continuous variable bounds and discrete choices for a vehicle candidate. Call this before proposing candidate values so they stay in bounds.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_requirement_kinds",
        "description": "List the engineering requirement kinds available for missions (used by check_mission, run_pareto_search, robust_check), with what each means and whether the robust (Monte Carlo) checker supports it.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "evaluate_candidate",
        "description": "Simulate one specific vehicle candidate with the real physics kernel: mass, manufacturing cost, 0-60mph time, and highway range at 65mph.",
        "input_schema": _candidate_input_schema(),
    },
    {
        "name": "check_mission",
        "description": "Check one candidate against a list of engineering requirements (a mission) at nominal conditions, returning pass/fail and a signed margin per requirement -- use this to explain exactly why a design does or doesn't meet a spec.",
        "input_schema": {
            "type": "object",
            "properties": {
                "candidate": _candidate_input_schema(),
                "requirements": _requirements_input_schema(REQUIREMENT_KINDS),
            },
            "required": ["candidate", "requirements"],
        },
    },
    {
        "name": "run_pareto_search",
        "description": "Run a real NSGA2 multi-objective search over the whole design space against a mission, returning the Pareto frontier (non-dominated designs trading off cost, mass, 0-60 time, and range). There is no single 'best' design -- use this to show the actual trade space. pop_size/n_gen default to 30/10 (a few seconds); raise them for a more thorough search at the cost of more time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "requirements": _requirements_input_schema(REQUIREMENT_KINDS),
                "pop_size": {"type": "integer", "minimum": 4, "maximum": 400},
                "n_gen": {"type": "integer", "minimum": 1, "maximum": 200},
                "seed": {"type": "integer"},
            },
            "required": ["requirements"],
        },
    },
    {
        "name": "sensitivity_analysis",
        "description": "Hold a base candidate fixed except for one field, evaluate it at each of several values for that field, and return how mass/cost/0-60/range change -- use this to answer 'how does X change if I increase Y'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "base_candidate": _candidate_input_schema(),
                "field": {"type": "string", "description": "Which candidate field to vary, e.g. 'battery_capacity_kwh' or 'motor_architecture'."},
                "values": {"type": "array", "items": {}, "description": "The values to try for that field (numbers for continuous fields, strings for discrete ones)."},
            },
            "required": ["base_candidate", "field", "values"],
        },
    },
    {
        "name": "robust_check",
        "description": "Monte Carlo-check a candidate against requirements across sampled operating uncertainty (payload, ambient temperature, road grade, tire wear, battery aging) instead of just the single nominal point -- use this before declaring a design good, since a design can pass check_mission and still fail most of the time under realistic conditions. Only max_acceleration_time_s, min_highway_range_mi, and max_braking_distance_m are supported (see list_requirement_kinds's robust_supported field).",
        "input_schema": {
            "type": "object",
            "properties": {
                "candidate": _candidate_input_schema(),
                "requirements": _requirements_input_schema(sorted(_ROBUST_REQUIREMENT_BUILDERS)),
                "n_samples": {"type": "integer", "minimum": 10, "maximum": 500},
                "seed": {"type": "integer"},
            },
            "required": ["candidate", "requirements"],
        },
    },
]

TOOL_DISPATCH: Dict[str, Callable[[dict], dict]] = {
    "get_design_space": tool_get_design_space,
    "list_requirement_kinds": tool_list_requirement_kinds,
    "evaluate_candidate": tool_evaluate_candidate,
    "check_mission": tool_check_mission,
    "run_pareto_search": tool_run_pareto_search,
    "sensitivity_analysis": tool_sensitivity_analysis,
    "robust_check": tool_robust_check,
}
