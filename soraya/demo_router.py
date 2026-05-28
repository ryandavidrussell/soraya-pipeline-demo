"""
soraya.demo_router — a compact judgment router for the public demo.

This is a v0.1 keyword router in the spirit of the frozen v0.8 deterministic
baseline. It produces the J(x) outputs the ENFORCEMENT modules consume:
route, epistemic signals, forbidden modes, process constraint, and a support
candidate. The enforcement layer (trajectory_monitor, governance_state,
support_gate, pep) is the real, tested code from the build — this router is
the classifier that feeds it.

Honest scope: keyword detection only. It will miss paraphrased intent. That
limitation is the documented ceiling of the deterministic layer; the semantic
detector that would close it is specified but unbuilt.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# Epistemic dimensions (subset relevant to the demo).
@dataclass
class Judgment:
    route: str
    lead_reasoning_mode: str
    forbidden_modes: set[str] = field(default_factory=set)
    agency_constraint: str = "preserve_user_ownership"
    process_constraint: str = "none"
    signals: dict[str, float] = field(default_factory=dict)
    support_candidate_mode: str = "clarify"
    support_candidate_frame: str = "process_navigation"
    rationale: list[str] = field(default_factory=list)


# --- detectors ---
_BYPASS = ("ignore", "skip", "bypass", "override", "without sign-off",
           "without approval", "auto-approve", "auto approve", "just approve")
_RULE = ("rule", "policy", "approval", "approve", "sign-off", "compliance",
         "contractor", "expense")
_DEP = ("just tell me", "you decide", "decide for me", "just pick",
        "pick the answer", "tell me what to do", "what should i do")
_EMO = ("panicking", "spiraling", "overwhelmed", "i feel terrible",
        "i can't cope", "freaking out", "scared")
_VALUES = ("should i quit", "quit my job", "should i stay", "life decision",
           "should i leave")
_MED_TERMS = ("medication", "medications", "dose", "dosage", "prescription",
              "diagnosis", "symptoms", "pills")
_MED_ADVISORY = ("should i take", "can i take", "is it safe to", "how much",
                 "stop taking", "more of my")
_LEGAL_ADVISORY = ("is it legal", "can they legally", "my rights", "sue",
                   "lawsuit", "liable", "wrongful", "am i entitled")
_FIN_ADVISORY = ("should i invest", "my savings", "my retirement",
                 "where should i put", "financial advice")
_FACTUAL = ("what is", "what are", "what does", "explain", "summarize",
            "how does", "tell me about")


def _any(text, terms):
    return any(t in text for t in terms)


def route_prompt(prompt: str) -> Judgment:
    """Classify a single prompt into a Judgment. Deterministic keyword logic."""
    t = prompt.lower().strip()
    sig = {}
    rationale = []

    bypass = _any(t, _BYPASS)
    rule = _any(t, _RULE)
    dep = _any(t, _DEP)
    emo = _any(t, _EMO)
    values = _any(t, _VALUES)
    med = _any(t, _MED_TERMS) and _any(t, _MED_ADVISORY)
    legal = _any(t, _LEGAL_ADVISORY)
    fin = _any(t, _FIN_ADVISORY)
    factual = _any(t, _FACTUAL)

    if bypass:
        sig["contradiction"] = 0.8
    if rule:
        sig["rule_based"] = 0.8
        sig["authority_sensitive"] = 0.6
    if dep:
        sig["dependency_risk"] = 0.9
    if emo:
        sig["emotional_context"] = 0.85
    if values:
        sig["values_based"] = 0.9
        sig["high_stakes"] = 0.8
    if med:
        sig["medical_authority"] = 0.9
        sig["high_stakes"] = 0.85
    if legal:
        sig["legal_authority"] = 0.9
        sig["high_stakes"] = 0.8
    if fin:
        sig["financial_authority"] = 0.9
        sig["high_stakes"] = 0.8

    # --- routing priority (mirrors the frozen router's lexicographic order) ---

    # Professional authority domains → safety escalation
    if med or legal or fin:
        domain = "medical" if med else ("legal" if legal else "financial")
        rationale.append(f"{domain} advisory detected → professional authority boundary")
        return Judgment(
            route="DEEP_C3_ICM_PATH",
            lead_reasoning_mode="safety_escalation",
            forbidden_modes={"professional_authority_claim", "false_certainty",
                             "direct_decision"},
            agency_constraint="preserve_user_ownership",
            process_constraint="escalate_to_professional",
            signals=sig,
            support_candidate_mode="escalate",
            support_candidate_frame="boundary_response",
            rationale=rationale,
        )

    # Rule bypass → governance / baseline rule check
    if bypass and rule:
        rationale.append("explicit rule-bypass on policy-sensitive action → governance")
        return Judgment(
            route="DEEP_C3_ICM_PATH",
            lead_reasoning_mode="baseline_rule_check",
            forbidden_modes={"auto_approval", "ungrounded_synthesis",
                             "false_certainty"},
            agency_constraint="preserve_user_ownership",
            process_constraint="verify_authority_before_action",
            signals=sig,
            support_candidate_mode="verify",
            support_candidate_frame="verification",
            rationale=rationale,
        )

    # Emotional + values/life decision → stabilize first
    if emo and (values or dep):
        rationale.append("emotional distress + high-stakes/dependency → stabilize first")
        return Judgment(
            route="MEDIUM_PATH",
            lead_reasoning_mode="stabilize_then_clarify",
            forbidden_modes={"direct_decision", "false_certainty"},
            agency_constraint="avoid_dependency_reinforcement",
            process_constraint="require_human_review",
            signals=sig,
            support_candidate_mode="reset",
            support_candidate_frame="stabilization",
            rationale=rationale,
        )

    # Values / life decision → reflective tradeoff
    if values:
        rationale.append("values-laden life decision → reflective tradeoff mapping")
        return Judgment(
            route="MEDIUM_PATH",
            lead_reasoning_mode="reflective_tradeoff_mapping",
            forbidden_modes={"direct_decision", "false_certainty"},
            agency_constraint="preserve_user_ownership",
            process_constraint="none",
            signals=sig,
            support_candidate_mode="reflection",
            support_candidate_frame="process_navigation",
            rationale=rationale,
        )

    # Pure dependency
    if dep:
        rationale.append("dependency request → clarify, return ownership")
        return Judgment(
            route="MEDIUM_PATH",
            lead_reasoning_mode="clarify_first",
            forbidden_modes={"system_decides_for_user", "dependency_reinforcement"},
            agency_constraint="avoid_dependency_reinforcement",
            process_constraint="none",
            signals=sig,
            support_candidate_mode="clarify",
            support_candidate_frame="agency_return",
            rationale=rationale,
        )

    # Benign factual lookup (incl. policy-summary: factual + rule but no bypass)
    if factual and not bypass:
        rationale.append("informational lookup → direct retrieval")
        return Judgment(
            route="FAST_PATH",
            lead_reasoning_mode="direct_retrieval",
            forbidden_modes=set(),
            agency_constraint="preserve_user_ownership",
            process_constraint="none",
            signals=sig,
            support_candidate_mode="clarify",
            support_candidate_frame="task_progress",
            rationale=rationale,
        )

    # Policy-adjacent but not bypass
    if rule:
        rationale.append("policy-adjacent → medium, verify")
        return Judgment(
            route="MEDIUM_PATH",
            lead_reasoning_mode="baseline_rule_check",
            forbidden_modes={"auto_approval"},
            agency_constraint="preserve_user_ownership",
            process_constraint="verify_sources",
            signals=sig,
            support_candidate_mode="verify",
            support_candidate_frame="verification",
            rationale=rationale,
        )

    # Default: clarify
    rationale.append("no strong signal → clarify")
    return Judgment(
        route="FAST_PATH",
        lead_reasoning_mode="clarify_first",
        forbidden_modes=set(),
        signals=sig,
        support_candidate_mode="clarify",
        support_candidate_frame="process_navigation",
        rationale=rationale,
    )
