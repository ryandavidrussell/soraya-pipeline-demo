"""
Unit tests for soraya.pep — Gamma Policy Enforcement Point (UP-005).

Frozen Invariant 3:
    Ledger flags are not enforcement. Gamma = block must physically prevent
    execution at the boundary.

The sixth test (gate bypassed) is the one that proves the hybrid design earns
its keep: if only the main-loop gate existed, a code path reaching a tool
without the gate would execute. The decorator fails closed and stops it.
"""
import pytest
from soraya.pep import (
    PolicyEnforcementPoint, enforced, BlockedActionError,
    EnforcementContext, set_enforcement_context, reset_enforcement_context,
    HALTING_DISPOSITIONS,
)


def test_gate_allows_when_disposition_allow():
    pep = PolicyEnforcementPoint()
    r = pep.enforce(disposition="allow", action="summarize", action_type="generation")
    assert r.execution_halted is False
    assert r.allowed_action_type == "generation"


def test_gate_halts_on_block():
    pep = PolicyEnforcementPoint()
    r = pep.enforce(disposition="block", action="send", action_type="message")
    assert r.execution_halted is True
    assert r.boundary_response_id is not None


def test_gate_halts_on_emergency_escalate():
    pep = PolicyEnforcementPoint()
    r = pep.enforce(disposition="emergency_escalate", action="grant_admin", action_type="tool")
    assert r.execution_halted is True


def test_decorator_blocks_side_effect_under_block():
    effects = []

    @enforced("tool")
    def do_thing():
        effects.append("ran")
        return "ok"

    token = set_enforcement_context(
        EnforcementContext(disposition="block", route="DEEP_C3_ICM_PATH", request_id="t")
    )
    try:
        with pytest.raises(BlockedActionError):
            do_thing()
        assert effects == [], "no side effect under block"
    finally:
        reset_enforcement_context(token)


def test_decorator_allows_under_allow():
    effects = []

    @enforced("tool")
    def do_thing():
        effects.append("ran")
        return "ok"

    token = set_enforcement_context(
        EnforcementContext(disposition="allow", route="FAST_PATH", request_id="t")
    )
    try:
        assert do_thing() == "ok"
        assert effects == ["ran"]
    finally:
        reset_enforcement_context(token)


def test_decorator_fails_closed_with_no_context():
    # THE SIXTH TEST: gate bypassed (no context set). The decorator must still
    # block. If only the main-loop gate existed, this action would execute.
    effects = []

    @enforced("message")
    def send_message(text):
        effects.append(text)
        return "sent"

    # Deliberately do NOT set an enforcement context — simulates a refactor
    # that reached a tool without passing through the gate.
    with pytest.raises(BlockedActionError) as exc:
        send_message("I quit")
    assert exc.value.result.enforcement_context_present is False
    assert exc.value.result.execution_halted is True
    assert exc.value.result.downstream_action_attempted is True
    assert effects == [], "fail-closed: no side effect without enforcement context"


def test_halting_dispositions_set():
    assert "block" in HALTING_DISPOSITIONS
    assert "emergency_escalate" in HALTING_DISPOSITIONS
    assert "allow" not in HALTING_DISPOSITIONS
    assert "require_review" not in HALTING_DISPOSITIONS


def test_gate_ledger_records_each_decision():
    pep = PolicyEnforcementPoint()
    pep.enforce("allow", "a", "generation")
    pep.enforce("block", "b", "tool")
    assert len(pep.ledger) == 2
    assert pep.ledger[1].execution_halted is True


def test_unknown_action_type_rejected():
    with pytest.raises(ValueError):
        @enforced("teleportation")
        def nope():
            pass
