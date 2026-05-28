"""
Soraya Unified Architecture v0.4.1 — Contract Stress Tests

These tests probe the gap between the implemented spine and the frozen spec.
Cases that require unimplemented modules (LR state, Gamma enforcement, H_t,
S(x) compatibility) are marked xfail with a precise reason.

Motto: Fail visibly. Patch narrowly. Promote one invariant at a time.

As each module is implemented, flip strict=True and remove the xfail marker.
"""
import json
from pathlib import Path
import pytest

CASES_PATH = Path(__file__).parent.parent / "scenario_packs" / "unified_pipeline_test_cases.v001.json"
CASES = json.loads(CASES_PATH.read_text())["cases"]


def get_case(case_id):
    return next(c for c in CASES if c["id"] == case_id)


# ---------------------------------------------------------------------------
# Capability probes — detect whether a module exists yet.
#
# These use importlib.util.find_spec, which reports module PRESENCE without
# importing it. This is deliberate: if a module exists but is broken (syntax
# error, bad import), find_spec still reports True, so the test body runs and
# FAILS for real instead of being hidden under xfail as "not present yet".
#
# When a module lands, its probe flips to True and the xfail condition becomes
# False — the invariant test then runs against real code.
# ---------------------------------------------------------------------------

import importlib.util


def _module_exists(module_name: str) -> bool:
    """Report module presence without importing. A broken-but-present module
    returns True, so its test fails honestly rather than hiding under xfail."""
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        # find_spec raises if a PARENT package is missing; that means absent.
        return False


def _has_conversation_state():
    return _module_exists("soraya.conversation_state")


def _has_trajectory_monitor():
    return _module_exists("soraya.trajectory_monitor")


def _has_gamma_enforcement():
    return _module_exists("soraya.enforcement")


def _has_reviewer_capacity():
    return _module_exists("soraya.governance_state")


def _has_support_gate():
    return _module_exists("soraya.support_gate")


# ---------------------------------------------------------------------------
# UP-004 — LR(H) dependency spiral must raise pre-judgment risk
# Invariant: LR(H) is pre-judgment
# ---------------------------------------------------------------------------

def test_up_004_case_is_well_formed():
    """The spec case itself must be valid even before implementation."""
    case = get_case("UP-004")
    assert case["invariant"] == "LR(H) is pre-judgment"
    assert len(case["given_history"]) >= 3
    assert "dependency_risk_delta_applied" in case["must_assert"]


@pytest.mark.xfail(
    condition=not (_has_conversation_state() and _has_trajectory_monitor()),
    reason="LR(H) requires ConversationState + trajectory_monitor; neither exists yet.",
    strict=True,
)
def test_up_004_lr_dependency_spiral_requires_prejudgment_state():
    from soraya.conversation_state import ConversationState
    from soraya.trajectory_monitor import trajectory_monitor

    case = get_case("UP-004")
    state = ConversationState()
    # Replay the escalating dependency history into session state.
    for msg in case["given_history"]:
        state.add_turn_from_text(msg)
    # Add the current turn too.
    state.add_turn_from_text(case["user_message"])

    lr = trajectory_monitor(state)
    # Invariant assertions (UP-004 must_assert):
    # trajectory_signal_exists + dependency_risk_delta_applied
    assert lr.pattern_scores["dependency_spiral"] > 0.5, "spiral must be detected"
    assert lr.feature_overrides["dependency_risk_delta"] > 0, "must raise risk pre-judgment"
    # forced_agency_constraint_includes_avoid_dependency_reinforcement
    assert "avoid_dependency_reinforcement" in lr.forced_agency_constraints
    # route floor proves LR can escalate based on session, not just this turn
    assert lr.route_floor == "MEDIUM_PATH"


# ---------------------------------------------------------------------------
# UP-005 — Gamma block must stop execution
# Invariant: Ledger flags are not enforcement
# ---------------------------------------------------------------------------

def test_up_005_case_is_well_formed():
    case = get_case("UP-005")
    assert case["given_authorization"]["authorized"] is False
    assert "generation_or_tool_execution_halted" in case["must_assert"]


@pytest.mark.xfail(
    condition=not _has_gamma_enforcement(),
    reason="Gamma=block enforcement requires a PolicyEnforcementPoint; none exists yet. "
           "Today the ledger can record review_required but cannot halt execution.",
    strict=True,
)
def test_up_005_gamma_block_must_stop_execution():
    from soraya.enforcement import PolicyEnforcementPoint

    case = get_case("UP-005")
    pep = PolicyEnforcementPoint()
    result = pep.enforce(
        disposition="block",
        action=case["given_authorization"]["requested_action"],
    )
    assert result.executed is False, "block must physically prevent execution"
    assert result.ledger_status == "blocked"


# ---------------------------------------------------------------------------
# UP-006 — Reviewer saturation must not downgrade route
# Invariant: Route/Disposition split
# ---------------------------------------------------------------------------

def test_up_006_case_is_well_formed():
    case = get_case("UP-006")
    assert case["expected_route"] == "DEEP_C3_ICM_PATH"
    assert case["given_h_t"]["state"] == "saturated"


@pytest.mark.xfail(
    condition=not _has_reviewer_capacity(),
    reason="H_t (reviewer capacity) does not exist in current routing state. "
           "Route/Disposition split cannot be enforced without it.",
    strict=True,
)
def test_up_006_reviewer_saturation_does_not_downgrade_route():
    from soraya.governance_state import ReviewerCapacity, resolve_disposition

    case = get_case("UP-006")
    h_t = ReviewerCapacity(
        state=case["given_h_t"]["state"],
        queue_depth=case["given_h_t"]["queue_depth"],
        queue_age_hours=case["given_h_t"]["queue_age_hours"],
        fatigue_factor=case["given_h_t"]["fatigue_factor"],
    )
    # The request is a DEEP-route legal-advice case. Route is computed upstream
    # (by J/B) and passed in; capacity must not alter it.
    route_in = "DEEP_C3_ICM_PATH"
    decision = resolve_disposition(route=route_in, authorized=True, h_t=h_t)

    # must_assert: route_remains_deep
    assert decision.route == "DEEP_C3_ICM_PATH", "saturation must NOT downgrade route"
    # must_assert: no_route_downgrade
    assert decision.route_downgraded is False
    # must_assert: disposition_changes_due_to_capacity
    assert decision.disposition in ("defer", "block", "emergency_escalate"), \
        "saturation must tighten disposition"
    # Prove the split: same route, healthy capacity yields a LESS restrictive
    # disposition — confirming capacity moved disposition, not route.
    healthy = ReviewerCapacity(state="healthy")
    healthy_decision = resolve_disposition(route=route_in, authorized=True, h_t=healthy)
    assert healthy_decision.route == decision.route, "route identical across capacity"
    assert healthy_decision.disposition == "require_review", \
        "healthy capacity allows review rather than defer"


# ---------------------------------------------------------------------------
# UP-007 — S(x) cannot softly bypass DEEP route
# Invariant: S(x) compatibility gate
# ---------------------------------------------------------------------------

def test_up_007_case_is_well_formed():
    case = get_case("UP-007")
    assert case["given_route"] == "DEEP_C3_ICM_PATH"
    assert case["support_candidate"]["frame"] == "task_progress"


@pytest.mark.xfail(
    condition=not _has_support_gate(),
    reason="S(x) compatibility validator does not exist. "
           "DEEP + tiny_step + task_progress would currently pass unchecked.",
    strict=True,
)
def test_up_007_support_mode_soft_bypass_rejected():
    from soraya.support_gate import validate_support_mode

    case = get_case("UP-007")
    result = validate_support_mode(
        candidate=case["support_candidate"],          # tiny_step + task_progress
        route=case["given_route"],                    # DEEP_C3_ICM_PATH
        disposition=case["given_disposition"],        # require_review
    )
    # must_assert: support_candidate_rejected
    assert result.compatibility_status == "fallback_applied"
    # must_assert: safe_fallback_selected
    assert result.final_frame != "task_progress", "DEEP must reject task_progress frame"
    assert result.final_frame in (
        "process_navigation", "verification", "stabilization", "boundary_response"
    )
    # The candidate is recorded alongside the final — ledger can show both.
    assert result.candidate_frame == "task_progress"
    assert result.fallback_reason is not None


# ---------------------------------------------------------------------------
# Meta-test: report the implementation gap as a visible summary.
# This always passes; it just prints the current state of the spine vs spec.
# ---------------------------------------------------------------------------

def test_zz_implementation_gap_report(capsys):
    modules = {
        "ConversationState": _has_conversation_state(),
        "trajectory_monitor (LR)": _has_trajectory_monitor(),
        "Gamma PEP enforcement": _has_gamma_enforcement(),
        "ReviewerCapacity (H_t)": _has_reviewer_capacity(),
        "S(x) compatibility gate": _has_support_gate(),
    }
    implemented = sum(modules.values())
    total = len(modules)
    print(f"\n=== v0.4.1 Implementation Gap: {implemented}/{total} modules present ===")
    for name, present in modules.items():
        print(f"  [{'X' if present else ' '}] {name}")
    print("=== Flip xfail → strict pass as each module lands ===")
    assert total - implemented >= 0  # always true; this is a report
