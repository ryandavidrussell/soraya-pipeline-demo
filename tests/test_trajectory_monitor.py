"""
Unit tests for soraya.trajectory_monitor (LR(H) v0.1).

Locks in the precision boundary found during UP-004 implementation:
a spiral is a cross-turn pattern, not a single dependent ask.
"""
from soraya.conversation_state import ConversationState
from soraya.trajectory_monitor import trajectory_monitor, max_route


def _state(*messages):
    s = ConversationState()
    for m in messages:
        s.add_turn_from_text(m)
    return s


def test_empty_state_produces_no_signal():
    lr = trajectory_monitor(ConversationState())
    assert lr.pattern_scores["dependency_spiral"] == 0.0
    assert lr.intervention_level == "none"
    assert lr.route_floor is None


def test_single_dependent_ask_is_not_a_spiral():
    # The precision boundary: one dependent turn is a single-turn signal,
    # handled by J(x), NOT a trajectory pattern.
    lr = trajectory_monitor(_state("What should I do about my schedule?"))
    assert lr.pattern_scores["dependency_spiral"] == 0.0
    assert lr.route_floor is None


def test_normal_task_talk_produces_no_signal():
    lr = trajectory_monitor(_state(
        "Can you help me outline a project plan?",
        "What should the first milestone be?",
        "Let me adjust the timeline.",
    ))
    assert lr.pattern_scores["dependency_spiral"] == 0.0
    assert lr.intervention_level == "none"


def test_one_dependent_turn_amid_normal_talk_does_not_fire_floor():
    lr = trajectory_monitor(_state(
        "Help me think through this budget.",
        "Just tell me what to do.",
        "Okay, I'll consider option one myself.",
    ))
    assert lr.route_floor is None


def test_two_dependent_turns_detect_spiral():
    lr = trajectory_monitor(_state(
        "What should I do here?",
        "Just decide for me.",
        "Pick the answer for me.",
    ))
    assert lr.pattern_scores["dependency_spiral"] > 0.5
    assert lr.route_floor == "MEDIUM_PATH"
    assert "avoid_dependency_reinforcement" in lr.forced_agency_constraints


def test_lr_never_lowers_risk():
    # LR feature_overrides are non-negative deltas by contract.
    lr = trajectory_monitor(_state(
        "Just tell me what to do.", "You decide for me.", "Pick the answer.",
    ))
    for delta in lr.feature_overrides.values():
        assert delta >= 0.0


def test_max_route_ordering():
    assert max_route("FAST_PATH", "MEDIUM_PATH") == "MEDIUM_PATH"
    assert max_route("DEEP_C3_ICM_PATH", "MEDIUM_PATH") == "DEEP_C3_ICM_PATH"
    assert max_route(None, "MEDIUM_PATH") == "MEDIUM_PATH"
    assert max_route("FAST_PATH", None) == "FAST_PATH"
