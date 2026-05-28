"""
soraya.conversation_state — session-local conversation state.

The smallest cage for the first dragon (UP-004): just enough turn history to
let the trajectory monitor evaluate cross-turn patterns. No persistence, no
disk, no memory governance entanglement. State lives for the session and dies
with it. Nothing here grants authority or stores user content beyond a hash.

Invariant support: LR(H) is pre-judgment. This module provides the H — the
session history the trajectory monitor reads BEFORE J(x) runs.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


def _hash_text(text: str) -> str:
    """Privacy-safe hash of user text. We store the hash, not the content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


@dataclass
class ConversationTurn:
    """A single recorded turn. Carries the signals trajectory analysis needs,
    not the raw text. user_text_preview is retained ONLY for detector input;
    it is the lowercased text used for pattern matching, not stored long-term."""
    turn_id: int
    user_text_hash: str
    user_text_preview: str  # lowercased, used by detectors this session only
    route: str | None = None
    mode: str | None = None
    dependency_risk_score: float = 0.0
    user_agency_score: float = 1.0
    review_required: bool = False
    user_action_required: str | None = None


@dataclass
class ConversationState:
    """Session-local turn history. No persistence. No cross-session linkage."""
    turns: list[ConversationTurn] = field(default_factory=list)

    def add_turn(self, turn: ConversationTurn) -> None:
        self.turns.append(turn)

    def add_turn_from_text(
        self,
        user_text: str,
        route: str | None = None,
        mode: str | None = None,
        dependency_risk_score: float = 0.0,
        user_agency_score: float = 1.0,
        review_required: bool = False,
        user_action_required: str | None = None,
    ) -> ConversationTurn:
        """Convenience for recording a turn directly from user text."""
        turn = ConversationTurn(
            turn_id=len(self.turns),
            user_text_hash=_hash_text(user_text),
            user_text_preview=user_text.lower().strip(),
            route=route,
            mode=mode,
            dependency_risk_score=dependency_risk_score,
            user_agency_score=user_agency_score,
            review_required=review_required,
            user_action_required=user_action_required,
        )
        self.turns.append(turn)
        return turn

    def last_n(self, n: int = 5) -> list[ConversationTurn]:
        return self.turns[-n:]

    def __len__(self) -> int:
        return len(self.turns)
