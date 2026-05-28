# Unified Pipeline Stress Tests (v0.4.1)

The first honest measurement of the gap between the implemented MVP spine and the
frozen Soraya Unified Architecture v0.4.1 spec.

## Purpose

Four stress cases (UP-004 through UP-007), each targeting one frozen invariant the
current MVP cannot yet satisfy. They are designed to **fail visibly** until the
corresponding module is implemented. This converts spec gaps into tracked engineering
debt instead of architectural vibes in a trench coat.

|Case  |Invariant                       |Missing module                                           |
|------|--------------------------------|---------------------------------------------------------|
|UP-004|LR(H) is pre-judgment           |`soraya.conversation_state` + `soraya.trajectory_monitor`|
|UP-005|Ledger flags are not enforcement|`soraya.enforcement` (Γ=block halt)                      |
|UP-006|Route/Disposition split         |`soraya.governance_state` (H_t)                          |
|UP-007|S(x) compatibility gate         |`soraya.support_gate`                                    |

## Test structure

Each case has two tests:

- `test_*_case_is_well_formed` — always passes; proves the scenario pack case is valid now.
- `test_*_<invariant>` — `xfail(strict=True)` until the module exists; runs against real
  code once it lands.

Plus `test_zz_implementation_gap_report`, which prints the current module-presence map.

## Capability probes use find_spec, not try/except import

Probes use `importlib.util.find_spec`, which reports module **presence** without importing.
This is deliberate. If a module exists but is broken (syntax error, bad import), `find_spec`
still reports `True`, so the test body runs and **fails for real** instead of being hidden
under `xfail` as “not present yet”. Catching a broad `Exception` on import would mask a
broken implementation as a missing one — a sneaky little gremlin. `find_spec` keeps the
suite brutally honest.

## Current baseline

```
pass=5  xfail=4  xpass=0  fail=0
=== v0.4.1 Implementation Gap: 0/5 modules present ===
  [ ] ConversationState
  [ ] trajectory_monitor (LR)
  [ ] Gamma PEP enforcement
  [ ] ReviewerCapacity (H_t)
  [ ] S(x) compatibility gate
```

This is not “incomplete.” It is an honest baseline. From here, every commit either closes
a named gap or it does not belong in the repo.

## Running

```bash
pip install -r requirements-dev.txt
pytest tests/test_unified_pipeline_contracts.py -v
```

## strict=True matters

The xfail markers are strict. When you implement a module, its probe flips to `True`, the
xfail condition becomes `False`, and the invariant test runs for real. If a test would XPASS
while still carrying a marker, strict mode flags it as a failure — forcing you to remove the
stale marker. The suite cannot quietly accumulate dead xfail decorations.

## Implementation order

1. `soraya/conversation_state.py` — session-local turn history, no persistence
1. `soraya/trajectory_monitor.py` — LR(H) output contract against ConversationState
1. Feed LR output into pre-judgment feature merge
1. `Γ` disposition object
1. `Γ = block` execution halt (PolicyEnforcementPoint)
1. `S_candidate / S_final` compatibility validator
1. Expand ledger to record LR, Γ, and S fallback data
1. Flip xfail → strict pass, one invariant at a time

UP-004 is the first dragon and the smallest cage: session-local state only, no persistent
memory, no governance nightmare in a trench coat.

## Motto

Fail visibly. Patch narrowly. Promote one invariant at a time.