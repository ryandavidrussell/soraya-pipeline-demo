"""
Unit tests for soraya.support_gate — the S(x) compatibility gate.

Frozen invariant (v0.4.1, Invariant 5):
    Helpful support that undermines safety classification is a soft bypass
    and must fail validation.

Locks in the canonical frame distinction and the deny-by-default posture.
"""
from soraya.support_gate import validate_support_mode
from soraya.support_modes import SupportMode


def _v(mode, frame, route, disposition, **kw):
    return validate_support_mode({"mode": mode, "frame": frame}, route, disposition, **kw)


def test_canonical_pair_frame_decides_validity():
    # The whole point of frames: same mode, opposite outcome.
    bad = _v("tiny_step", "task_progress", "DEEP_C3_ICM_PATH", "require_review")
    assert bad.compatibility_status == "fallback_applied"
    assert bad.final_frame != "task_progress"

    good = _v("tiny_step", "process_navigation", "DEEP_C3_ICM_PATH", "require_review")
    assert good.compatibility_status == "passed"
    assert good.final_mode == "tiny_step"
    assert good.final_frame == "process_navigation"


def test_deep_rejects_task_progress_for_any_mode():
    for mode in ("tiny_step", "momentum", "reflection", "triage"):
        r = _v(mode, "task_progress", "DEEP_C3_ICM_PATH", "require_review")
        assert r.compatibility_status == "fallback_applied", f"{mode} should be rejected"


def test_deep_rejects_momentum_entirely():
    # momentum has no valid (mode, frame) entry on DEEP.
    for frame in ("task_progress", "process_navigation", "verification"):
        r = _v("momentum", frame, "DEEP_C3_ICM_PATH", "require_review")
        assert r.compatibility_status == "fallback_applied"


def test_disposition_narrows_beyond_route():
    # verify/verification is fine on DEEP normally...
    ok = _v("verify", "verification", "DEEP_C3_ICM_PATH", "require_review")
    assert ok.compatibility_status == "passed"
    # ...but block disposition requires boundary_response.
    blocked = _v("verify", "verification", "DEEP_C3_ICM_PATH", "block")
    assert blocked.compatibility_status == "fallback_applied"
    assert blocked.final_frame == "boundary_response"


def test_block_disposition_forces_boundary_response():
    r = _v("refuse", "boundary_response", "DEEP_C3_ICM_PATH", "block")
    assert r.compatibility_status == "passed"


def test_fast_route_is_permissive():
    for mode, frame in (("momentum", "task_progress"), ("tiny_step", "task_progress")):
        r = _v(mode, frame, "FAST_PATH", "allow")
        assert r.compatibility_status == "passed"


def test_forbidden_mode_rejected():
    r = _v("escalate", "boundary_response", "DEEP_C3_ICM_PATH", "require_review",
           forbidden_modes={"escalate"})
    assert r.compatibility_status == "fallback_applied"
    assert "forbidden" in r.fallback_reason


def test_lr_disallowed_mode_rejected():
    r = _v("momentum", "task_progress", "FAST_PATH", "allow",
           lr_support_restrictions={"disallowed_modes": {"momentum"}})
    assert r.compatibility_status == "fallback_applied"
    assert "trajectory monitor" in r.fallback_reason


def test_lr_required_frame_enforced():
    r = _v("verify", "verification", "MEDIUM_PATH", "require_review",
           lr_support_restrictions={"required_frame": "agency_return"})
    assert r.compatibility_status == "fallback_applied"


def test_candidate_and_final_both_recorded():
    # Ledger needs both: what was proposed and what was used.
    r = _v("tiny_step", "task_progress", "DEEP_C3_ICM_PATH", "require_review")
    assert r.candidate_mode == "tiny_step"
    assert r.candidate_frame == "task_progress"
    assert r.final_mode != "tiny_step" or r.final_frame != "task_progress"
    assert r.compatibility_rule_id


def test_accepts_supportmode_dataclass():
    sm = SupportMode(mode="verify", frame="verification")
    r = validate_support_mode(sm, "MEDIUM_PATH", "verify")
    assert r.compatibility_status == "passed"
