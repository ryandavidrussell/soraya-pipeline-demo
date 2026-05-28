# Γ PEP Enforcement Design (UP-005)

*Design document. Decides where enforcement physically lives before any code is written.*
*Spec reference: Soraya Unified Architecture v0.4.1, Frozen Invariant 3.*

-----

## 1. Purpose

Frozen Invariant 3:

> Ledger flags are not enforcement. Γ = block must physically prevent execution
> at the PEP/tool/API/retrieval boundary.

Today the system can compute `Γ = block` and record it in the ledger. Nothing
physically prevents the code from continuing past it. This document decides
**where the execution boundary lives** so that `block` means halt, not log.

The question is not philosophical. It is physical: when `Γ.disposition = block`,
which line of code is guaranteed not to run, and what structure guarantees it?

-----

## 2. Enforcement Boundary Options

### A. Main-loop gate

A single checkpoint in the pipeline. After Γ is resolved, the main loop inspects
the disposition and refuses to proceed to generation/action if blocked.

- **Pro**: one obvious place; easy to read; matches the pipeline pseudocode.
- **Con**: single point of failure. If a future code path calls a tool without
  going through the main loop (a refactor, a new feature, an agent sub-call),
  the gate is bypassed. The guarantee is only as strong as the discipline of
  every caller.

### B. Tool-call decorator

Every tool/action function is wrapped. The decorator checks the current Γ
disposition before allowing the underlying function to execute.

- **Pro**: enforcement travels with the action, not the caller. A tool cannot
  execute regardless of how it was reached.
- **Con**: requires every action to be registered/decorated. An un-decorated
  action is silently unprotected. Also needs access to the current disposition
  (context propagation).

### C. Middleware wrapper

A layer between the pipeline and all side-effecting subsystems (tools, memory,
APIs, file I/O). All effects route through it.

- **Pro**: comprehensive; one choke point for all side effects.
- **Con**: heaviest to build; requires all subsystems to be reachable only
  through the middleware. Easy to get partially right and feel safe while a
  direct path remains.

### D. Hybrid: main-loop gate + tool decorator  ← SELECTED

Main-loop gate blocks generation/tool-planning when Γ forbids continuation.
Tool decorator independently blocks any individual tool call even if the
main-loop gate is bypassed or refactored away.

- **Pro**: belt and suspenders. Two independent guarantees. A refactor that
  removes one still leaves the other. The decorator catches what the gate
  misses; the gate catches what isn’t a tool call (e.g. generation).
- **Con**: slight duplication. Acceptable — governance systems need suspenders
  because belts get refactored by interns.

-----

## 3. Decision: Hybrid Enforcement

**The main-loop gate** is the primary, readable enforcement point. It sits after
Γ resolution and before any generation or action. It is where most blocks happen
and where the ledger records the disposition.

**The tool-call decorator** is the independent backstop. Every side-effecting
action is wrapped. It reads the current disposition from an enforcement context
and refuses to execute the underlying function if blocked — even if the main-loop
gate was somehow skipped.

Rationale: the two boundaries fail independently. The gate protects against the
common case and covers non-tool actions (generation). The decorator protects
against the dangerous case — a code path that reaches a tool without passing the
gate. Neither alone is sufficient: the gate can be refactored around, and the
decorator can’t block a generation (which isn’t a registered tool). Together they
cover the full action surface.

-----

## 4. Action Types and Halt Semantics

“Halt” means something concrete and different per action type:

|Action type                |What “halt” physically means                                  |
|---------------------------|--------------------------------------------------------------|
|Response generation        |The LLM is not called; a boundary response is returned instead|
|Tool call                  |The tool function does not execute; no side effect occurs     |
|Memory write               |No turn/fact is persisted to ConversationState or memory      |
|External API call          |The HTTP/RPC request is never issued                          |
|File write                 |No bytes are written to disk                                  |
|Notification / message send|No message leaves the system                                  |

The decorator covers tool call, memory write, external API, file write, and
message send (all side-effecting). The main-loop gate covers response generation
(not a registered tool) and is the first line for all of the above.

-----

## 5. Required Behavior by Γ Disposition

|Disposition         |Required behavior                                                            |
|--------------------|-----------------------------------------------------------------------------|
|`allow`             |Proceed normally                                                             |
|`clarify`           |Generate a clarification request only; no substantive action                 |
|`verify`            |Require a verification step before any substantive action                    |
|`require_review`    |Prepare a review packet only; no resolution/action                           |
|`defer`             |No execution; return a checkpoint response naming the next human/process step|
|`block`             |Halt the action path; return a boundary response; no side effects            |
|`emergency_escalate`|Halt the ordinary path; emit an escalation response; no side effects         |

The two halting dispositions (`block`, `emergency_escalate`) are the decorator’s
hard stops. `defer` also prevents execution but returns a checkpoint rather than
a boundary. `require_review` and `verify` permit bounded, non-executing support.

-----

## 6. Enforcement Context Propagation

The decorator needs to know the current disposition. Options:

- **Thread/context-local variable** set by the main-loop gate before any action
  is reachable. The decorator reads it. Cleanest for a single-request flow.
- **Explicit disposition argument** threaded into every action call. Most
  explicit, most verbose.

Decision: a context object (`EnforcementContext`) set once per request by the
gate, read by the decorator. It carries `disposition`, `route`, and a request id
for ledger correlation. If the context is unset when a decorated action is
called, the decorator **fails closed** — it blocks, because an action reaching a
tool with no enforcement context means the gate was bypassed, which is exactly
the dangerous case the decorator exists to catch.

Fail-closed is the only safe default. An unset context is not “allow by absence”;
it is “block by absence.”

-----

## 7. Ledger Contract

Each enforcement decision records:

```
enforcement: {
    requested_action:            str,        # what was attempted
    requested_action_type:       str,        # generation|tool|memory|api|file|message
    gamma_disposition:           str,        # allow|...|block|emergency_escalate
    enforcement_boundary_used:   str,        # main_loop_gate | tool_decorator | both
    execution_halted:            bool,
    downstream_action_attempted: bool,       # did anything try to run past the gate?
    allowed_action_type:         str | null, # what WAS permitted, if anything
    boundary_response_id:        str | null,
    enforcement_context_present: bool        # false => fail-closed triggered
}
```

`downstream_action_attempted = True` while `execution_halted = True` is the
signal that the decorator caught something the gate missed — a refactor smell
worth alerting on.

-----

## 8. Test Contract for UP-005

Given `Γ = block`:

1. No tool call occurs (decorated tool’s underlying function never runs).
1. No memory write occurs.
1. No action payload is executed (no external API, no file write, no send).
1. The ledger records `execution_halted = True` and `gamma_disposition = block`.
1. The user receives a boundary response.

Additional belt-and-suspenders test:

1. With the main-loop gate deliberately bypassed (simulating a refactor that
   forgot the gate), a decorated tool call under `block` **still** does not
   execute — the decorator fails closed, `enforcement_context` check holds, and
   `downstream_action_attempted = True` is recorded.

This sixth test is the one that proves the hybrid design earns its keep. If only
the gate existed, this test could not pass.

-----

## 9. Minimal Implementation Plan

```
soraya/pep.py
    - EnforcementContext (disposition, route, request_id)
    - class PolicyEnforcementPoint:
        enforce(disposition, action, action_type) -> EnforcementResult
        (the main-loop gate)
    - @enforced(action_type) decorator
        reads current EnforcementContext; fails closed if unset;
        blocks if disposition in {block, emergency_escalate};
        else calls the underlying function
    - HALTING_DISPOSITIONS = {"block", "emergency_escalate"}

tests/test_gamma_pep_enforcement.py
    - the six tests from the test contract above
```

When UP-005 flips:

```
pass=9  xfail=0  xpass=0  gap=5/5
```

That is the moment the running repo catches the frozen spec’s core stress surface.
Every invariant the architecture exists to enforce is then structurally enforced,
not merely asserted — and regression-locked by unit tests.

-----

## 10. What This Does NOT Cover

This design enforces the disposition that Γ produces. It does not:

- Decide Γ’s disposition (that is `resolve_disposition`, already built in UP-006).
- Implement the full agent runtime (tool registry, agent loop). The decorator
  is defined; wiring it to a real tool set is downstream integration work.
- Handle distributed/multi-process enforcement. This is single-process. A
  distributed PEP is a future concern with its own design pass.

The boundary is decided. The code is small. The decision was the work.