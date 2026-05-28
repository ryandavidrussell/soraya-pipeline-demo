"""
soraya.governance_state — H_t, the human review capacity component of G_t.

Implements the v0.4.1 Route/Disposition split (§5, Frozen Invariant 2):

    Reviewer saturation may change execution disposition.
    Reviewer saturation may NOT downgrade epistemic or safety classification.

H_t is a contained data structure describing review capacity. It feeds the
disposition resolver, which decides what is ALLOWED to happen given capacity —
never what the situation IS. Route classification is computed elsewhere (J/B)
and is immutable to capacity pressure.
"""
from __future__ import annotations

from dataclasses import dataclass


# Capacity state ordering, least to most constrained.
_STATE_ORDER = {"healthy": 0, "elevated": 1, "saturated": 2, "critical": 3}

# Route ordering for the disposition logic (mirror of trajectory_monitor).
_ROUTE_ORDER = {"FAST_PATH": 0, "MEDIUM_PATH": 1, "DEEP_C3_ICM_PATH": 2}


@dataclass
class ReviewerCapacity:
    """H_t — human oversight capacity. Read by the disposition resolver."""
    state: str = "healthy"          # healthy | elevated | saturated | critical
    queue_depth: int = 0
    queue_age_hours: float = 0.0
    fatigue_factor: float = 0.0     # [0,1]
    severity_mix: float = 0.0       # proportion DEEP in queue, [0,1]
    turnaround_sla_hours: float = 24.0

    def is_saturated(self) -> bool:
        return _STATE_ORDER.get(self.state, 0) >= _STATE_ORDER["saturated"]

    @classmethod
    def derive_state(
        cls,
        queue_depth: int,
        queue_age_hours: float,
        fatigue_factor: float,
        turnaround_sla_hours: float = 24.0,
    ) -> str:
        """Derive a capacity state from raw signals. Deterministic, auditable.
        This is a v0.1 heuristic; thresholds are governed parameters."""
        # Critical: queue is both deep and stale, or reviewers exhausted.
        if (queue_age_hours >= 2 * turnaround_sla_hours and queue_depth > 200) \
                or fatigue_factor >= 0.9:
            return "critical"
        if queue_depth > 100 or queue_age_hours >= turnaround_sla_hours \
                or fatigue_factor >= 0.7:
            return "saturated"
        if queue_depth > 30 or queue_age_hours >= 0.5 * turnaround_sla_hours \
                or fatigue_factor >= 0.4:
            return "elevated"
        return "healthy"


# Dispositions, least to most restrictive.
DISPOSITIONS = (
    "allow", "clarify", "verify", "require_review",
    "defer", "block", "emergency_escalate",
)


@dataclass
class DispositionDecision:
    """Output of the capacity-aware disposition resolver."""
    route: str               # STABLE — never adjusted by capacity
    disposition: str
    h_t_state: str
    reason: str
    route_downgraded: bool = False   # must always be False; asserted in tests


def resolve_disposition(
    route: str,
    authorized: bool,
    h_t: ReviewerCapacity,
) -> DispositionDecision:
    """Compute execution disposition from route, authorization, and capacity.

    THE INVARIANT: route is an input and an output, unchanged. Capacity affects
    only `disposition`. There is no code path here that rewrites `route`.
    """
    # Unauthorized actions are blocked regardless of capacity.
    if not authorized:
        return DispositionDecision(
            route=route,
            disposition="block",
            h_t_state=h_t.state,
            reason="unauthorized_action",
        )

    route_rank = _ROUTE_ORDER.get(route, 0)

    # DEEP route under capacity pressure: disposition tightens, route holds.
    if route_rank == _ROUTE_ORDER["DEEP_C3_ICM_PATH"]:
        if h_t.state == "critical":
            disp = "emergency_escalate"
            reason = "deep_route_critical_capacity"
        elif h_t.is_saturated():
            disp = "defer"
            reason = "deep_route_saturated_capacity_defer_not_downgrade"
        else:
            disp = "require_review"
            reason = "deep_route_normal_capacity"
        return DispositionDecision(route=route, disposition=disp,
                                   h_t_state=h_t.state, reason=reason)

    # MEDIUM route.
    if route_rank == _ROUTE_ORDER["MEDIUM_PATH"]:
        if h_t.state == "critical":
            disp = "defer"
            reason = "medium_route_critical_capacity"
        elif h_t.is_saturated():
            disp = "require_review"
            reason = "medium_route_saturated_capacity"
        else:
            disp = "verify"
            reason = "medium_route_normal_capacity"
        return DispositionDecision(route=route, disposition=disp,
                                   h_t_state=h_t.state, reason=reason)

    # FAST route: low consequence, allowed even under pressure.
    return DispositionDecision(
        route=route,
        disposition="allow",
        h_t_state=h_t.state,
        reason="fast_route",
    )
