"""
soraya.pipeline — the unified v0.4.1 pipeline orchestrator for the demo.

Runs Π(x) through the real, tested enforcement modules:
    Stage 1a  trajectory_monitor (LR)        [ENFORCED]
    Stage 2   demo_router (J)                 [demo classifier]
    Stage 2   route_floor = max_route(...)    [ENFORCED — LR floor]
    Stage 3   resolve_disposition (Γ + H_t)   [ENFORCED]
    Stage 4b  validate_support_mode (S gate)  [ENFORCED]
    Stage 5   PolicyEnforcementPoint (Γ PEP)  [ENFORCED]
    Stage 7   assemble ledger entry

Returns a structured trace for display.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict

from soraya.conversation_state import ConversationState
from soraya.trajectory_monitor import trajectory_monitor, max_route
from soraya.governance_state import ReviewerCapacity, resolve_disposition
from soraya.support_gate import validate_support_mode
from soraya.support_modes import SupportMode
from soraya.pep import (
    PolicyEnforcementPoint, enforced, BlockedActionError,
    EnforcementContext, set_enforcement_context, reset_enforcement_context,
)
from soraya import demo_router


@dataclass
class StageTrace:
    name: str
    status: str          # enforced | demo | halt | pep_active
    summary: str
    detail: dict = field(default_factory=dict)


@dataclass
class PipelineResult:
    final_status: str
    route: str
    disposition: str
    user_facing: str
    stages: list[StageTrace] = field(default_factory=list)
    ledger_entry: dict = field(default_factory=dict)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


# A stand-in side-effecting action, guarded by the real PEP decorator.
_side_effects: list[str] = []


@enforced("tool")
def _execute_action(action: str) -> str:
    _side_effects.append(action)
    return f"executed: {action}"


def run_pipeline(
    prompt: str,
    prior_turns: list[str] | None = None,
    reviewer_state: str = "healthy",
    authorized: bool = True,
    requested_action: str | None = None,
) -> PipelineResult:
    """Run the full v0.4.1 pipeline and return a display trace."""
    prior_turns = prior_turns or []
    stages: list[StageTrace] = []
    _side_effects.clear()

    # --- Stage 1a: Trajectory Monitor (LR) — runs BEFORE judgment ---
    state = ConversationState()
    for turn in prior_turns:
        state.add_turn_from_text(turn)
    state.add_turn_from_text(prompt)
    lr = trajectory_monitor(state)

    lr_detail = {
        "dependency_spiral": lr.pattern_scores["dependency_spiral"],
        "intervention_level": lr.intervention_level,
        "route_floor": lr.route_floor,
        "forced_agency_constraints": sorted(lr.forced_agency_constraints),
        "dependency_risk_delta": lr.feature_overrides["dependency_risk_delta"],
    }
    lr_summary = (
        f"spiral={lr.pattern_scores['dependency_spiral']:.2f} · "
        f"intervention={lr.intervention_level}"
        + (f" · floor={lr.route_floor}" if lr.route_floor else "")
    )
    stages.append(StageTrace("1a · Trajectory Monitor (LR)", "enforced",
                             lr_summary, lr_detail))

    # --- Stage 2: Judgment Router (demo classifier) ---
    j = demo_router.route_prompt(prompt)
    route_j = j.route
    # Apply LR route floor (enforced).
    route_final = max_route(route_j, lr.route_floor)
    # Merge LR-forced constraints and forbidden modes.
    forbidden = set(j.forbidden_modes) | set(lr.forbidden_mode_additions)
    agency = (next(iter(lr.forced_agency_constraints))
              if lr.forced_agency_constraints else j.agency_constraint)

    j_detail = {
        "route_from_judgment": route_j,
        "route_floor_from_LR": lr.route_floor,
        "route_final": route_final,
        "lead_reasoning_mode": j.lead_reasoning_mode,
        "forbidden_modes": sorted(forbidden),
        "agency_constraint": agency,
        "process_constraint": j.process_constraint,
        "signals": {k: round(v, 2) for k, v in j.signals.items()},
        "rationale": j.rationale,
    }
    j_summary = (
        f"route={route_final} · mode={j.lead_reasoning_mode}"
        + (f" (floored from {route_j})" if route_final != route_j else "")
    )
    stages.append(StageTrace("2 · Judgment Router", "demo", j_summary, j_detail))

    # --- Stage 3: Governance + Disposition (Γ + H_t) — ENFORCED ---
    h_t = ReviewerCapacity(state=reviewer_state)
    disp = resolve_disposition(route=route_final, authorized=authorized, h_t=h_t)
    disp_detail = {
        "route_in": route_final,
        "route_out": disp.route,           # must equal route_in
        "route_downgraded": disp.route_downgraded,  # must be False
        "h_t_state": disp.h_t_state,
        "disposition": disp.disposition,
        "reason": disp.reason,
    }
    disp_summary = (
        f"disposition={disp.disposition} · route held at {disp.route} "
        f"(downgraded={disp.route_downgraded})"
    )
    stages.append(StageTrace("3 · Governance + Disposition (Γ, H_t)", "enforced",
                             disp_summary, disp_detail))

    # --- Stage 4b: Support Compatibility Gate — ENFORCED ---
    candidate = SupportMode(mode=j.support_candidate_mode,
                            frame=j.support_candidate_frame)
    sv = validate_support_mode(
        candidate=candidate,
        route=disp.route,
        disposition=disp.disposition,
        forbidden_modes=forbidden,
        lr_support_restrictions=lr.support_mode_restrictions,
    )
    sv_detail = {
        "candidate": f"{sv.candidate_mode} / {sv.candidate_frame}",
        "final": f"{sv.final_mode} / {sv.final_frame}",
        "compatibility_status": sv.compatibility_status,
        "rule_id": sv.compatibility_rule_id,
        "fallback_reason": sv.fallback_reason,
    }
    sv_summary = (
        f"{sv.candidate_mode}/{sv.candidate_frame} → "
        f"{sv.final_mode}/{sv.final_frame} [{sv.compatibility_status}]"
    )
    stages.append(StageTrace("4b · Support Compatibility Gate (S)", "enforced",
                             sv_summary, sv_detail))

    # --- Stage 5: Γ PEP Enforcement — ENFORCED, physical halt ---
    pep = PolicyEnforcementPoint()
    action = requested_action or "respond_to_user"
    action_type = "tool" if requested_action else "generation"
    gate = pep.enforce(disposition=disp.disposition, action=action,
                       action_type=action_type, request_id="demo")

    # Demonstrate the decorator backstop on a real side-effecting action.
    decorator_blocked = None
    if requested_action:
        token = set_enforcement_context(
            EnforcementContext(disposition=disp.disposition,
                               route=disp.route, request_id="demo"))
        try:
            try:
                _execute_action(requested_action)
                decorator_blocked = False
            except BlockedActionError:
                decorator_blocked = True
        finally:
            reset_enforcement_context(token)

    pep_detail = {
        "gamma_disposition": gate.gamma_disposition,
        "execution_halted": gate.execution_halted,
        "boundary_response_id": gate.boundary_response_id,
        "requested_action": action,
        "decorator_blocked_side_effect": decorator_blocked,
        "side_effects_executed": list(_side_effects),
    }
    pep_summary = (
        f"halted={gate.execution_halted}"
        + (f" · side-effect blocked={decorator_blocked}"
           if requested_action else "")
    )
    pep_status = "halt" if gate.execution_halted else "pep_active"
    stages.append(StageTrace("5 · Γ PEP Enforcement", pep_status, pep_summary, pep_detail))

    # --- Final status ---
    if gate.execution_halted or disp.disposition in ("block", "emergency_escalate"):
        final_status = "blocked_or_review_required"
        user_facing = _boundary_message(disp, j)
    elif disp.disposition in ("defer", "require_review"):
        final_status = "passed_gross_checks_human_review_required"
        user_facing = _review_message(disp, j, sv)
    else:
        final_status = "passed_gross_checks_no_review_required"
        user_facing = _normal_message(j, sv)

    # --- Stage 7: Ledger entry (hash-chained shape) ---
    ledger = {
        "prompt_hash": _hash(prompt),
        "trajectory": lr_detail,
        "judgment": {
            "route_final": route_final,
            "lead_reasoning_mode": j.lead_reasoning_mode,
            "forbidden_modes": sorted(forbidden),
            "agency_constraint": agency,
            "process_constraint": j.process_constraint,
        },
        "authority": {
            "authorized": authorized,
            "h_t_state": disp.h_t_state,
            "disposition": disp.disposition,
            "route_downgraded": disp.route_downgraded,
        },
        "support": sv_detail,
        "enforcement": {
            "execution_halted": gate.execution_halted,
            "decorator_blocked_side_effect": decorator_blocked,
        },
        "final_status": final_status,
    }
    ledger["entry_hash"] = _hash(json.dumps(ledger, sort_keys=True))

    return PipelineResult(
        final_status=final_status,
        route=disp.route,
        disposition=disp.disposition,
        user_facing=user_facing,
        stages=stages,
        ledger_entry=ledger,
    )


def _boundary_message(disp, j) -> str:
    if j.process_constraint == "escalate_to_professional":
        return ("This needs a qualified professional. I can help you frame the "
                "question or find the right kind of expert, but I won't give "
                "advice that should come from a licensed professional.")
    return ("I can't proceed with this action. It requires authority or review "
            "that isn't satisfied here. I can prepare what a reviewer would "
            "need, but I won't execute it.")


def _review_message(disp, j, sv) -> str:
    return ("I can help you prepare this for review, but I won't resolve it "
            "myself. Here's what the next checkpoint needs — the decision "
            "stays with you and the reviewer.")


def _normal_message(j, sv) -> str:
    if j.agency_constraint == "avoid_dependency_reinforcement":
        return ("I'll help you think this through, but I won't make the call "
                "for you. Let's lay out your options so the decision stays "
                "yours.")
    return "Happy to help with that directly."
