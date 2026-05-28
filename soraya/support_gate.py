"""
soraya.support_gate — the S(x) compatibility gate (v0.4.1 patch P2, §7.1).

Frozen invariant (v0.4.1, Invariant 5):
    S(x) is valid only if route-compatible, disposition-compatible, and
    constraint-compatible. Helpful support that undermines safety classification
    is a soft bypass and must fail validation.

This closes the fourth hard protection: helpful support cannot softly bypass
governance. A support mode that is locally helpful but undermines the route's
safety posture is rejected, and the safest compatible fallback is selected.
"""
from __future__ import annotations

from dataclasses import dataclass

from soraya.support_modes import SupportMode

# Route ordering (mirror of other modules).
_ROUTE_ORDER = {"FAST_PATH": 0, "MEDIUM_PATH": 1, "DEEP_C3_ICM_PATH": 2}


# --- Compatibility matrix (v0.4.1 §7.2) ------------------------------------
# For each route, which (mode, frame) combinations are permitted.
# Anything not explicitly allowed is rejected by default — deny-by-default is
# the safe posture for a soft-bypass gate.

# DEEP: only safety/process/verification work. No task progress. No momentum.
_DEEP_ALLOWED = {
    ("escalate", "boundary_response"),
    ("escalate", "process_navigation"),
    ("refuse", "boundary_response"),
    ("verify", "verification"),
    ("reset", "stabilization"),
    ("clarify", "process_navigation"),
    ("clarify", "boundary_response"),
    ("tiny_step", "process_navigation"),   # "pause, save, route to reviewer"
    ("triage", "stabilization"),
    ("reflection", "stabilization"),
}

# MEDIUM: process work, verification, bounded support. No approval-implying
# momentum, no task-advancing tiny_step.
_MEDIUM_ALLOWED = {
    ("clarify", "process_navigation"),
    ("clarify", "verification"),
    ("triage", "process_navigation"),
    ("reset", "stabilization"),
    ("reflection", "process_navigation"),
    ("reflection", "stabilization"),
    ("verify", "verification"),
    ("escalate", "process_navigation"),
    ("escalate", "boundary_response"),
    ("tiny_step", "process_navigation"),
    ("refuse", "boundary_response"),
}

# FAST: low-consequence; most things allowed including task progress.
_FAST_ALLOWED = None  # None = permissive (anything not forbidden by F/LR)

_ROUTE_MATRIX = {
    "DEEP_C3_ICM_PATH": _DEEP_ALLOWED,
    "MEDIUM_PATH": _MEDIUM_ALLOWED,
    "FAST_PATH": _FAST_ALLOWED,
}


# --- Disposition constraints (v0.4.1 §7.3) ---------------------------------
# Disposition further narrows what frame is permitted, independent of route.
_DISPOSITION_REQUIRED_FRAMES = {
    "block": {"boundary_response"},
    "emergency_escalate": {"boundary_response", "stabilization"},
    "defer": {"boundary_response", "process_navigation"},
    "require_review": {"process_navigation", "verification", "boundary_response"},
    "verify": {"verification", "process_navigation"},
    # allow / clarify: no extra frame restriction beyond route matrix
}


@dataclass
class SupportValidationResult:
    candidate_mode: str
    candidate_frame: str
    final_mode: str
    final_frame: str
    compatibility_status: str           # passed | fallback_applied
    compatibility_rule_id: str
    fallback_reason: str | None = None


def _frame_allowed_by_disposition(frame: str, disposition: str) -> bool:
    required = _DISPOSITION_REQUIRED_FRAMES.get(disposition)
    if required is None:
        return True
    return frame in required


def _mode_frame_allowed_by_route(mode: str, frame: str, route: str) -> bool:
    allowed = _ROUTE_MATRIX.get(route, _FAST_ALLOWED)
    if allowed is None:  # FAST / permissive
        return True
    return (mode, frame) in allowed


def _safest_fallback(route: str, disposition: str,
                     lr_restrictions: dict | None) -> tuple[str, str, str]:
    """Pick the safest compatible support mode for the given context.

    Ordering of safety, most to least restrictive:
        block/emergency      -> refuse/escalate + boundary_response
        defer                -> escalate + process_navigation
        require_review/verify -> verify + verification
        DEEP otherwise        -> clarify + process_navigation
        MEDIUM otherwise      -> clarify + process_navigation
        FAST                  -> clarify + process_navigation
    """
    if disposition in ("block", "emergency_escalate"):
        return "refuse", "boundary_response", "fallback_block_boundary"
    if disposition == "defer":
        return "escalate", "process_navigation", "fallback_defer_process_nav"
    if disposition in ("require_review", "verify"):
        return "verify", "verification", "fallback_review_verification"
    if route == "DEEP_C3_ICM_PATH":
        return "clarify", "process_navigation", "fallback_deep_process_nav"
    return "clarify", "process_navigation", "fallback_default_process_nav"


def validate_support_mode(
    candidate: SupportMode | dict,
    route: str,
    disposition: str,
    forbidden_modes: set[str] | None = None,
    lr_support_restrictions: dict | None = None,
) -> SupportValidationResult:
    """Validate a candidate support mode against route, disposition, forbidden
    modes, and LR support-mode restrictions. Return the candidate if compatible,
    else the safest compatible fallback.

    A locally helpful mode that undermines the route's safety posture is a soft
    bypass and MUST fail here."""
    if isinstance(candidate, dict):
        cand_mode = candidate.get("mode", "")
        cand_frame = candidate.get("frame", "")
    else:
        cand_mode = candidate.mode
        cand_frame = candidate.frame

    forbidden_modes = forbidden_modes or set()
    lr_restrictions = lr_support_restrictions or {}

    # Check 1 — forbidden modes (from F(x) or LR additions).
    if cand_mode in forbidden_modes:
        m, f, rid = _safest_fallback(route, disposition, lr_restrictions)
        return SupportValidationResult(
            cand_mode, cand_frame, m, f, "fallback_applied", rid,
            fallback_reason=f"mode '{cand_mode}' is forbidden",
        )

    # Check 2 — LR disallowed modes.
    lr_disallowed = lr_restrictions.get("disallowed_modes", set())
    if cand_mode in lr_disallowed:
        m, f, rid = _safest_fallback(route, disposition, lr_restrictions)
        return SupportValidationResult(
            cand_mode, cand_frame, m, f, "fallback_applied", rid,
            fallback_reason=f"mode '{cand_mode}' disallowed by trajectory monitor",
        )

    # Check 3 — route compatibility (the soft-bypass core).
    if not _mode_frame_allowed_by_route(cand_mode, cand_frame, route):
        m, f, rid = _safest_fallback(route, disposition, lr_restrictions)
        return SupportValidationResult(
            cand_mode, cand_frame, m, f, "fallback_applied", rid,
            fallback_reason=(
                f"({cand_mode}, {cand_frame}) not permitted on {route}"
            ),
        )

    # Check 4 — disposition compatibility.
    if not _frame_allowed_by_disposition(cand_frame, disposition):
        m, f, rid = _safest_fallback(route, disposition, lr_restrictions)
        return SupportValidationResult(
            cand_mode, cand_frame, m, f, "fallback_applied", rid,
            fallback_reason=(
                f"frame '{cand_frame}' not permitted under disposition '{disposition}'"
            ),
        )

    # Check 5 — LR required frame (if trajectory monitor demands one).
    lr_required_frame = lr_restrictions.get("required_frame")
    if lr_required_frame and cand_frame != lr_required_frame:
        m, f, rid = _safest_fallback(route, disposition, lr_restrictions)
        return SupportValidationResult(
            cand_mode, cand_frame, m, f, "fallback_applied", rid,
            fallback_reason=f"trajectory requires frame '{lr_required_frame}'",
        )

    # All checks passed — candidate is compatible.
    return SupportValidationResult(
        cand_mode, cand_frame, cand_mode, cand_frame, "passed",
        "compatible",
    )
