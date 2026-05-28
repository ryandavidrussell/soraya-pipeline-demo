"""
soraya.pep — Policy Enforcement Point (Γ enforcement, UP-005).

Frozen Invariant 3 (v0.4.1):
    Ledger flags are not enforcement. Γ = block must physically prevent
    execution at the PEP/tool/API/retrieval boundary.

Design: hybrid enforcement (see docs/gamma-pep-enforcement-design.md).
    - PolicyEnforcementPoint.enforce(...)  — the main-loop gate
    - @enforced(action_type) decorator     — independent per-action backstop

The decorator FAILS CLOSED: if no EnforcementContext is set when a decorated
action runs, it blocks. An action reaching a tool with no enforcement context
means the gate was bypassed — exactly the dangerous case the decorator exists
to catch.
"""
from __future__ import annotations

import contextvars
import functools
from dataclasses import dataclass, field

# Dispositions that physically halt execution.
HALTING_DISPOSITIONS = frozenset({"block", "emergency_escalate"})

# Dispositions that prevent execution but return a checkpoint, not a hard stop.
NON_EXECUTING_DISPOSITIONS = frozenset({"defer", "require_review", "clarify", "verify"})

ACTION_TYPES = frozenset({
    "generation", "tool", "memory", "api", "file", "message",
})


@dataclass
class EnforcementContext:
    """Set once per request by the main-loop gate; read by the decorator."""
    disposition: str
    route: str
    request_id: str


# Context-local: the decorator reads this. Unset => fail closed.
_current_context: contextvars.ContextVar[EnforcementContext | None] = \
    contextvars.ContextVar("soraya_enforcement_context", default=None)


def set_enforcement_context(ctx: EnforcementContext | None) -> contextvars.Token:
    return _current_context.set(ctx)


def reset_enforcement_context(token: contextvars.Token) -> None:
    _current_context.reset(token)


def get_enforcement_context() -> EnforcementContext | None:
    return _current_context.get()


@dataclass
class EnforcementResult:
    requested_action: str
    requested_action_type: str
    gamma_disposition: str
    enforcement_boundary_used: str          # main_loop_gate | tool_decorator | both
    execution_halted: bool
    downstream_action_attempted: bool = False
    allowed_action_type: str | None = None
    boundary_response_id: str | None = None
    enforcement_context_present: bool = True


class BlockedActionError(Exception):
    """Raised by the decorator when a halted action is attempted."""
    def __init__(self, result: EnforcementResult):
        self.result = result
        super().__init__(
            f"Action '{result.requested_action}' halted: "
            f"disposition={result.gamma_disposition}, "
            f"context_present={result.enforcement_context_present}"
        )


class PolicyEnforcementPoint:
    """The main-loop gate. Inspects a disposition before any action proceeds."""

    def __init__(self):
        self._ledger: list[EnforcementResult] = []

    def enforce(
        self,
        disposition: str,
        action: str,
        action_type: str = "generation",
        request_id: str = "req",
    ) -> EnforcementResult:
        """Primary gate. Returns a result; execution_halted=True means the
        caller MUST NOT proceed to the action."""
        halted = disposition in HALTING_DISPOSITIONS
        result = EnforcementResult(
            requested_action=action,
            requested_action_type=action_type,
            gamma_disposition=disposition,
            enforcement_boundary_used="main_loop_gate",
            execution_halted=halted,
            downstream_action_attempted=False,
            allowed_action_type=None if halted else action_type,
            boundary_response_id=(f"boundary:{request_id}" if halted else None),
            enforcement_context_present=True,
        )
        self._ledger.append(result)
        return result

    @property
    def ledger(self) -> list[EnforcementResult]:
        return self._ledger


def enforced(action_type: str = "tool"):
    """Decorator: independent per-action backstop. Blocks the underlying
    function if the current disposition halts, or if no context is set
    (fail closed)."""
    if action_type not in ACTION_TYPES:
        raise ValueError(f"unknown action_type: {action_type}")

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            ctx = get_enforcement_context()
            # Fail closed: no context means the gate was bypassed.
            if ctx is None:
                raise BlockedActionError(EnforcementResult(
                    requested_action=fn.__name__,
                    requested_action_type=action_type,
                    gamma_disposition="unknown_no_context",
                    enforcement_boundary_used="tool_decorator",
                    execution_halted=True,
                    downstream_action_attempted=True,
                    enforcement_context_present=False,
                ))
            if ctx.disposition in HALTING_DISPOSITIONS:
                raise BlockedActionError(EnforcementResult(
                    requested_action=fn.__name__,
                    requested_action_type=action_type,
                    gamma_disposition=ctx.disposition,
                    enforcement_boundary_used="tool_decorator",
                    execution_halted=True,
                    downstream_action_attempted=True,
                    enforcement_context_present=True,
                ))
            # Permitted — run the real action.
            return fn(*args, **kwargs)
        return wrapper
    return decorator
