"""
soraya.trajectory_monitor — LR(H), the Least-Resonance Trajectory Monitor.

Implements the v0.4.1 LR(H) output contract as a PRE-JUDGMENT constraint
provider. It reads ConversationState (the session history H) and produces
feature overrides, forced agency constraints, forbidden-mode additions, and an
optional route floor — all of which feed into J(x) BEFORE judgment routing.

Frozen invariant (v0.4.1):
  LR(H) constrains judgment by modifying pre-judgment features and constraints.
  It does not patch J(x) after governance disposition has already been computed.

LR merge rules enforced here:
  - MAY raise risk-bearing features (deltas are non-negative)
  - MAY add agency constraints
  - MAY add forbidden modes
  - MAY set a route floor
  - MAY NOT lower risk, remove forbidden modes, create evidence, or grant authority

This is v0.1: deterministic pattern detection only. Scope is the dependency
spiral pattern needed for UP-004, with stubs for the other patterns so the
contract shape is complete and future detectors slot in without interface change.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from soraya.conversation_state import ConversationState

# Route ordering for the route floor rule.
_ROUTE_ORDER = {"FAST_PATH": 0, "MEDIUM_PATH": 1, "DEEP_C3_ICM_PATH": 2}


def max_route(a: str | None, b: str | None) -> str | None:
    """Route_final = max_route(Route_J, LR.route_floor). Higher wins."""
    if a is None:
        return b
    if b is None:
        return a
    return a if _ROUTE_ORDER.get(a, 0) >= _ROUTE_ORDER.get(b, 0) else b


@dataclass
class LRResult:
    """The LR(H) output contract (v0.4.1 §8.1)."""
    health_score: float = 1.0
    pattern_scores: dict[str, float] = field(default_factory=lambda: {
        "dependency_spiral": 0.0,
        "reassurance_loop": 0.0,
        "authority_collapse": 0.0,
        "over_explanation_loop": 0.0,
        "avoidance_loop": 0.0,
        "repetitive_attractor": 0.0,
    })
    detected_patterns: list[str] = field(default_factory=list)
    intervention_level: str = "none"  # none|observe|constrain|route_floor|emergency
    feature_overrides: dict[str, float] = field(default_factory=lambda: {
        "dependency_risk_delta": 0.0,
        "unsafe_reliance_risk_delta": 0.0,
        "authority_confusion_delta": 0.0,
        "uncertainty_delta": 0.0,
    })
    forced_agency_constraints: set[str] = field(default_factory=set)
    forbidden_mode_additions: set[str] = field(default_factory=set)
    route_floor: str | None = None
    support_mode_restrictions: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)


# --- Dependency-spiral detector (the UP-004 target) -------------------------

# Phrases that signal the user is delegating the decision rather than owning it.
_DEPENDENCY_MARKERS = (
    "just tell me what to do",
    "you decide",
    "decide for me",
    "just pick",
    "pick the answer",
    "i don't want to choose",
    "i dont want to choose",
    "tell me what to do",
    "just tell me",
    "what should i do",
)


def _turn_shows_dependency(preview: str) -> bool:
    return any(marker in preview for marker in _DEPENDENCY_MARKERS)


def _score_dependency_spiral(state: ConversationState, window: int = 5) -> tuple[float, list[int]]:
    """Score the dependency-spiral pattern over the recent window.

    A spiral is repeated delegation across turns, not a single dependent ask.
    Score scales with the count and consecutiveness of dependent turns.
    Returns (score in [0,1], contributing turn ids)."""
    recent = state.last_n(window)
    if not recent:
        return 0.0, []

    dependent_turns = [t for t in recent if _turn_shows_dependency(t.user_text_preview)]
    contributing = [t.turn_id for t in dependent_turns]
    count = len(dependent_turns)

    # A spiral is a CROSS-TURN pattern. A single dependent ask is not a spiral —
    # it is a single-turn signal that J(x) handles on its own. Trajectory
    # monitoring only speaks when there is a trajectory: 2+ dependent turns.
    if count < 2:
        return 0.0, []

    # Base score from proportion of recent turns showing dependency.
    proportion = count / len(recent)

    # Escalation bonus: a run of consecutive dependent turns is a true spiral,
    # not just scattered uncertainty.
    longest_run = 0
    current_run = 0
    for t in recent:
        if _turn_shows_dependency(t.user_text_preview):
            current_run += 1
            longest_run = max(longest_run, current_run)
        else:
            current_run = 0

    run_bonus = min(longest_run / window, 1.0) * 0.5
    score = min(proportion * 0.6 + run_bonus, 1.0)
    return score, contributing


def trajectory_monitor(state: ConversationState, window: int = 5) -> LRResult:
    """Evaluate session trajectory and return the LR(H) constraint object.

    Runs BEFORE J(x). Output feeds the pre-judgment feature merge."""
    result = LRResult()

    if len(state) == 0:
        return result

    # --- Dependency spiral (implemented) ---
    spiral_score, contributing = _score_dependency_spiral(state, window)
    result.pattern_scores["dependency_spiral"] = round(spiral_score, 3)

    # Other patterns: contract present, detectors deferred (v0.1 scope).
    # They remain 0.0 until implemented, keeping the interface stable.

    # --- Intervention decision for dependency spiral ---
    if spiral_score >= 0.6:
        result.detected_patterns.append("dependency_spiral")
        result.intervention_level = "route_floor"
        # Raise risk pre-judgment (non-negative delta — never lowers risk).
        result.feature_overrides["dependency_risk_delta"] = round(spiral_score, 3)
        result.feature_overrides["unsafe_reliance_risk_delta"] = round(spiral_score * 0.5, 3)
        # Force agency-preserving constraint.
        result.forced_agency_constraints.add("avoid_dependency_reinforcement")
        result.forced_agency_constraints.add("return_next_action_to_user")
        # Add forbidden modes that would reinforce the spiral.
        result.forbidden_mode_additions.add("system_decides_for_user")
        result.forbidden_mode_additions.add("dependency_reinforcement")
        # Set a route floor: the session warrants at least MEDIUM even if this
        # single turn looks benign.
        result.route_floor = "MEDIUM_PATH"
        # Restrict support modes away from anything that decides for the user.
        result.support_mode_restrictions = {
            "required_frame": "agency_return",
            "disallowed_modes": {"momentum"},
        }
    elif spiral_score >= 0.3:
        result.detected_patterns.append("dependency_spiral")
        result.intervention_level = "constrain"
        result.feature_overrides["dependency_risk_delta"] = round(spiral_score, 3)
        result.forced_agency_constraints.add("avoid_dependency_reinforcement")
    elif spiral_score > 0.0:
        result.intervention_level = "observe"

    # Health score declines as the strongest pattern intensifies.
    worst = max(result.pattern_scores.values())
    result.health_score = round(1.0 - worst, 3)

    result.evidence = {
        "contributing_turn_ids": contributing,
        "current_health_score": result.health_score,
        "trend_window": window,
        "rationale_codes": (
            ["dependency_spiral_detected"] if "dependency_spiral" in result.detected_patterns
            else []
        ),
    }
    return result
