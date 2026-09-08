from apex.robust.design_selection import select_robust_design
from apex.robust.release_assurance import build_design_release_certificate, verify_design_release_certificate
from apex.robust.signature_algorithm import Architecture as SignatureArchitecture, ablation as signature_ablation, select_architecture as signature_select, sensitivity as signature_sensitivity
"""FastAPI scientific service: a thin HTTP wrapper around the apex package.

Synchronous and blocking by design. "Manage simulations and orchestrate jobs" is
explicitly the Rust backend's job per the platform proposal's own split ("Rust...
manage[s] simulations and orchestrate[s] jobs while Python runs the scientific
workers") -- this service's entire responsibility is "do the computation, return
the result." The Rust backend wraps the slow /pareto call in an async background
job with polling so the frontend never blocks on it; this service doesn't need to
know that's happening.

    uvicorn service.main:app --reload --port 8001
"""

import os
import time
import uuid

from fastapi import FastAPI, HTTPException

from apex.design import DesignCandidate, PlatformContext, build_vehicle, default_design_space
from apex.market import BENCHMARK_VEHICLES
from apex.optimize import _PYMOO_AVAILABLE, default_objectives, run_pareto_search
from apex.physics import constant_speed_range_km, zero_to_sixty_s
from apex.physics.constants import MPH_TO_MPS
from apex.surrogate import generate_dataset, train_and_compare
from apex.copilot import build_response as build_copilot_response

from .mission_registry import ROBUST_REQUIREMENT_KINDS, REQUIREMENT_KINDS, build_mission, build_robust_mission
from .schemas import (
    AgentChatRequest,
    AgentChatResponse,
    AgentToolCallSummary,
    BenchmarkVehicleResponse,
    CandidateSpec,
    ContinuousVariableSpec,
    CostBreakdown,
    DesignSpaceResponse,
    DiscreteVariableSpec,
    EvaluateResponse,
    MassBreakdown,
    ParetoPointResponse,
    ParetoRequest,
    ParetoResponse,
    RobustCheckRequest, RobustSelectRequest,
    RobustCheckResponse,
    RobustRequirementResultResponse,
)

# The agent extra (anthropic + agent/) is optional -- the core service (evaluate,
# pareto, metadata) must keep working even if it isn't installed. Import failure
# here disables only the /agent/chat route below, not the whole app.
try:
    import anthropic

    from agent.engineer_agent import run_agent_turn

    _AGENT_AVAILABLE = True
except ImportError:
    _AGENT_AVAILABLE = False

app = FastAPI(title="APEX Scientific Service", version="0.1.0")

@app.middleware("http")
async def request_context(request, call_next):
    request_id=request.headers.get("X-Request-ID") or f"apex-{uuid.uuid4().hex[:16]}"
    started=time.perf_counter()
    response=await call_next(request)
    response.headers["X-Request-ID"]=request_id
    response.headers["X-Response-Time-Ms"]=f"{(time.perf_counter()-started)*1000:.3f}"
    response.headers["X-Engineering-Release"]="REVIEW_ONLY"
    return response

_HIGHWAY_SPEED_MPS = 65.0 * MPH_TO_MPS


def _to_design_candidate(spec: CandidateSpec) -> DesignCandidate:
    return DesignCandidate(**spec.model_dump())


@app.get("/health")
def health() -> dict:
    # Keep the stable health contract intentionally minimal for load balancers and existing clients.
    return {"status": "ok"}


@app.get("/capabilities")
def capabilities() -> dict:
    return {
        "pareto_available": bool(_PYMOO_AVAILABLE),
        "robust_design_selection": True,
        "agent_available": bool(_AGENT_AVAILABLE),
        "production_write_allowed": False,
    }


@app.get("/governance/signature")
def governance_signature() -> dict:
    """Return the executable ARCH-SHIELD reference decision and its counterfactuals."""
    candidates = [
        SignatureArchitecture("cheap", 40_000, 420, 7.5, 0.82),
        SignatureArchitecture("shielded", 44_000, 410, 7.7, 0.96),
        SignatureArchitecture("long", 48_000, 520, 8.4, 0.94),
    ]
    constraints = {"min_range_km": 400, "max_zero_to_sixty_s": 8.0, "max_cost_usd": 46_000}
    selected = signature_select(candidates, **constraints)
    baseline = signature_ablation(candidates, **constraints)
    sensitivity = signature_sensitivity(candidates, 0.9, **constraints)
    return {
        "status": "HUMAN_GATED_REFERENCE",
        "signature_algorithm": "ARCH-SHIELD-v1",
        "decision": selected.__dict__ if selected else None,
        "baseline": baseline.__dict__ if baseline else None,
        "sensitivity": sensitivity.__dict__ if sensitivity else None,
        "objective": "minimum cost after reliability, range, acceleration, and budget gates",
        "counterfactual": "reliability-floor ablation",
        "evidence_artifact": "artifacts/fortune50_capability_benchmark.json",
        "autonomous_execution": False,
    }


@app.get("/requirement-kinds")
def requirement_kinds() -> list:
    return REQUIREMENT_KINDS


@app.get("/robust-requirement-kinds")
def robust_requirement_kinds() -> list:
    return ROBUST_REQUIREMENT_KINDS


@app.post("/robust-check", response_model=RobustCheckResponse)
def robust_check(request: RobustCheckRequest) -> RobustCheckResponse:
    try:
        candidate = _to_design_candidate(request.candidate)
        vehicle, _ = build_vehicle(candidate, PlatformContext())
        mission = build_robust_mission("robust check", [r.model_dump() for r in request.requirements])
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    results = mission.evaluate(vehicle, n_samples=request.n_samples, seed=request.seed)
    return RobustCheckResponse(
        robustly_feasible=bool(mission.is_feasible(results)),
        n_samples=request.n_samples,
        requirements=[
            RobustRequirementResultResponse(
                name=r.name,
                unit=r.unit,
                threshold=r.threshold,
                reliability_target=r.reliability_target,
                fraction_satisfied=r.fraction_satisfied,
                satisfied=bool(r.satisfied),
                nominal_value=r.nominal_value,
                worst_value=r.worst_value,
            )
            for r in results
        ],
    )


@app.post("/robust-select")
def robust_select(request: RobustSelectRequest) -> dict:
    try:
        candidates=[_to_design_candidate(c) for c in request.candidates]
        mission=build_robust_mission("robust shortlist selection", [r.model_dump() for r in request.requirements])
        return select_robust_design(candidates,mission,n_samples=request.n_samples,seed=request.seed,cvar_alpha=request.cvar_alpha)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/robust-select/certificate")
def robust_select_certificate(request: RobustSelectRequest) -> dict:
    try:
        candidates=[_to_design_candidate(c) for c in request.candidates]
        mission=build_robust_mission("robust shortlist selection", [r.model_dump() for r in request.requirements])
        selection=select_robust_design(candidates,mission,n_samples=request.n_samples,seed=request.seed,cvar_alpha=request.cvar_alpha)
        shortlist=[c.as_dict() for c in candidates]
        requirements=[r.model_dump() for r in request.requirements]
        certificate=build_design_release_certificate(selection,mission_requirements=requirements,shortlist=shortlist)
        return {"selection":selection,"certificate":certificate,"verification":verify_design_release_certificate(certificate)}
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/benchmark-vehicles", response_model=list[BenchmarkVehicleResponse])
def benchmark_vehicles() -> list[BenchmarkVehicleResponse]:
    return [
        BenchmarkVehicleResponse(
            name=v.name,
            epa_range_mi=v.epa_range_mi,
            msrp_usd=v.msrp_usd,
            vehicle_type=v.vehicle_type,
            drivetrain=v.drivetrain,
        )
        for v in BENCHMARK_VEHICLES
    ]


@app.get("/surrogate-comparison")
def surrogate_comparison(n_samples: int = 80, seed: int = 7) -> dict:
    """Expose a reproducible GP-vs-Random-Forest model review for the workstation."""
    if n_samples < 40 or n_samples > 220:
        raise HTTPException(422, "n_samples must be between 40 and 220")
    dataset = generate_dataset(default_design_space(), n_samples=n_samples, seed=seed)
    comparisons = train_and_compare(dataset, test_size=0.2, seed=seed)
    rows = []
    for comparison in comparisons:
        rows.append({
            "target": comparison.target_name,
            "gaussian_process": comparison.gp_metrics.__dict__,
            "random_forest": comparison.rf_metrics.__dict__,
            "selected_for_exploration": "gaussian_process" if comparison.gp_metrics.rmse <= comparison.rf_metrics.rmse else "random_forest",
        })
    return {
        "dataset": "physics-generated Latin-hypercube simulation dataset",
        "n_samples": n_samples,
        "seed": seed,
        "comparison": rows,
        "selection_policy": "lower holdout RMSE for exploration; GP uncertainty remains preferred when tied",
        "claim_boundary": "surrogate accuracy is measured against APEX physics outputs, not production vehicle telemetry",
    }


@app.get("/design-space", response_model=DesignSpaceResponse)
def design_space_metadata() -> DesignSpaceResponse:
    space = default_design_space()
    return DesignSpaceResponse(
        continuous=[ContinuousVariableSpec(name=v.name, lower=v.lower, upper=v.upper, unit=v.unit) for v in space.continuous],
        discrete=[DiscreteVariableSpec(name=v.name, choices=list(v.choices)) for v in space.discrete],
    )


@app.post("/evaluate", response_model=EvaluateResponse)
def evaluate(spec: CandidateSpec) -> EvaluateResponse:
    try:
        candidate = _to_design_candidate(spec)
        vehicle, report = build_vehicle(candidate, PlatformContext())
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return EvaluateResponse(
        vehicle_name=vehicle.name,
        mass_kg=vehicle.mass_kg,
        manufacturing_cost_usd=report.total_manufacturing_cost,
        zero_to_sixty_s=zero_to_sixty_s(vehicle),
        range_mi=constant_speed_range_km(vehicle, _HIGHWAY_SPEED_MPS) * 0.621371,
        cost_breakdown=CostBreakdown(
            glider_usd=report.glider_cost,
            battery_usd=report.battery_cost,
            motor_usd=report.motor_cost,
            tire_delta_usd=report.tire_cost_delta,
            total_usd=report.total_manufacturing_cost,
        ),
        mass_breakdown=MassBreakdown(
            glider_kg=report.glider_mass_kg,
            battery_kg=report.battery_mass_kg,
            motor_kg=report.motor_mass_kg,
            tire_delta_kg=report.tire_mass_delta_kg,
            total_kg=report.total_mass_kg,
        ),
    )


@app.post("/pareto", response_model=ParetoResponse)
def pareto(request: ParetoRequest) -> ParetoResponse:
    try:
        mission = build_mission(request.mission.name, [r.model_dump() for r in request.mission.requirements])
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not _PYMOO_AVAILABLE:
        raise HTTPException(status_code=501, detail="pymoo is not installed; install declared APEX project dependencies to enable Pareto search")
    design_space = default_design_space()
    objectives = default_objectives()
    result = run_pareto_search(
        design_space,
        mission,
        objectives,
        pop_size=request.pop_size,
        n_gen=request.n_gen,
        seed=request.seed,
    )

    points = [
        ParetoPointResponse(candidate=CandidateSpec(**point.candidate.as_dict()), objective_values=point.objective_values)
        for point in result.points
    ]
    return ParetoResponse(n_points=len(points), points=points)


if _AGENT_AVAILABLE:

    @app.post("/agent/chat", response_model=AgentChatResponse)
    def agent_chat(request: AgentChatRequest) -> AgentChatResponse:
        # Prefer the portfolio-wide Gemini copilot when configured.  The deterministic
        # fallback keeps the chat demonstrable without leaking a provider dependency.
        if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
            result = build_copilot_response(request.message, {
                "evidence": "deterministic vehicle physics, robust checks, and surrogate comparison",
                "mode": "review-only",
            })
            return AgentChatResponse(final_text=result["answer"], tool_calls=[], hops_used=0, forced_final=False)
        # Fail closed when no provider is configured. The deterministic copilot is
        # intentionally available through the explicit Gemini path above; silently
        # returning a synthetic answer here would make a missing production secret
        # look like a successful provider-backed response.
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise HTTPException(
                status_code=401,
                detail="ANTHROPIC_API_KEY is required when Gemini is not configured",
            )

        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
        try:
            result = run_agent_turn(client, request.message)
        except anthropic.AuthenticationError as exc:
            raise HTTPException(status_code=401, detail=f"agent credentials rejected: {exc}") from exc
        except anthropic.APIError as exc:
            raise HTTPException(status_code=502, detail=f"agent LLM call failed: {exc}") from exc

        return AgentChatResponse(
            final_text=result.final_text,
            tool_calls=[
                AgentToolCallSummary(name=c.name, input=c.input, result=c.result, is_error=c.is_error) for c in result.tool_calls
            ],
            hops_used=result.hops_used,
            forced_final=result.forced_final,
        )
else:

    @app.post("/agent/chat")
    def agent_chat_unavailable(request: AgentChatRequest) -> AgentChatResponse:
        result = build_copilot_response(request.message, {
            "evidence": "deterministic vehicle physics, robust checks, and surrogate comparison",
            "mode": "review-only",
        })
        return AgentChatResponse(final_text=result["answer"], tool_calls=[], hops_used=0, forced_final=False)
