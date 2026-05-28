"""
Unit tests for soraya.governance_state — the Route/Disposition split.

Frozen invariant (v0.4.1, Invariant 2):
    Reviewer saturation may change execution disposition.
    Reviewer saturation may NOT downgrade epistemic or safety classification.

These tests lock in that route is immutable to capacity pressure.
"""
import pytest
from soraya.governance_state import ReviewerCapacity, resolve_disposition


ALL_ROUTES = ["FAST_PATH", "MEDIUM_PATH", "DEEP_C3_ICM_PATH"]
ALL_STATES = ["healthy", "elevated", "saturated", "critical"]


def test_route_never_changes_across_any_capacity_state():
    # The core invariant, exhaustively: route_out == route_in, always.
    for route in ALL_ROUTES:
        for state in ALL_STATES:
            h = ReviewerCapacity(state=state)
            d = resolve_disposition(route=route, authorized=True, h_t=h)
            assert d.route == route, f"{route}/{state} downgraded to {d.route}"
            assert d.route_downgraded is False


def test_deep_route_saturated_defers_not_downgrades():
    h = ReviewerCapacity(state="saturated", queue_depth=500,
                         queue_age_hours=72, fatigue_factor=0.95)
    d = resolve_disposition(route="DEEP_C3_ICM_PATH", authorized=True, h_t=h)
    assert d.route == "DEEP_C3_ICM_PATH"
    assert d.disposition == "defer"


def test_deep_route_critical_emergency_escalates():
    h = ReviewerCapacity(state="critical")
    d = resolve_disposition(route="DEEP_C3_ICM_PATH", authorized=True, h_t=h)
    assert d.route == "DEEP_C3_ICM_PATH"
    assert d.disposition == "emergency_escalate"


def test_disposition_tightens_as_capacity_degrades():
    # Same DEEP route; disposition must become MORE restrictive, not less,
    # as capacity worsens. Proves capacity moves disposition.
    order = ["require_review", "require_review", "defer", "emergency_escalate"]
    for state, expected in zip(ALL_STATES, order):
        d = resolve_disposition("DEEP_C3_ICM_PATH", True, ReviewerCapacity(state=state))
        assert d.disposition == expected, f"{state}: got {d.disposition}"


def test_unauthorized_always_blocks():
    for route in ALL_ROUTES:
        for state in ALL_STATES:
            d = resolve_disposition(route, authorized=False, h_t=ReviewerCapacity(state=state))
            assert d.disposition == "block"
            assert d.route == route  # even blocking does not rewrite route


def test_fast_route_allowed_under_pressure():
    # FAST is low-consequence; saturation should not block it.
    d = resolve_disposition("FAST_PATH", True, ReviewerCapacity(state="critical"))
    assert d.route == "FAST_PATH"
    assert d.disposition == "allow"


def test_derive_state_thresholds():
    assert ReviewerCapacity.derive_state(0, 0, 0.0) == "healthy"
    assert ReviewerCapacity.derive_state(50, 5, 0.2) == "elevated"
    assert ReviewerCapacity.derive_state(150, 30, 0.5) == "saturated"
    assert ReviewerCapacity.derive_state(500, 72, 0.95) == "critical"
    # Fatigue alone can drive critical even with a short queue.
    assert ReviewerCapacity.derive_state(10, 1, 0.95) == "critical"
