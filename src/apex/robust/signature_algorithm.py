"""ARCH-SHIELD reference contract for governance and reproducible review."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Architecture:
    name: str
    cost_usd: float
    range_km: float
    zero_to_sixty_s: float
    reliability: float


def select_architecture(
    candidates: list[Architecture],
    *,
    min_range_km: float,
    max_zero_to_sixty_s: float,
    max_cost_usd: float,
    reliability_floor: float = 0.90,
) -> Architecture | None:
    """Select the least-cost feasible design after a reliability gate."""
    feasible = [
        c for c in candidates
        if c.range_km >= min_range_km
        and c.zero_to_sixty_s <= max_zero_to_sixty_s
        and c.cost_usd <= max_cost_usd
        and c.reliability >= reliability_floor
    ]
    return min(feasible, key=lambda c: (c.cost_usd, -c.reliability, -c.range_km)) if feasible else None


def ablation(candidates: list[Architecture], **kwargs) -> Architecture | None:
    """Remove the ARCH-SHIELD reliability gate for a declared ablation."""
    kwargs["reliability_floor"] = 0.0
    return select_architecture(candidates, **kwargs)


def sensitivity(candidates: list[Architecture], cost_multiplier: float, **kwargs) -> Architecture | None:
    """Perturb the cost constraint and return the resulting decision."""
    kwargs["max_cost_usd"] = kwargs["max_cost_usd"] * float(cost_multiplier)
    return select_architecture(candidates, **kwargs)
