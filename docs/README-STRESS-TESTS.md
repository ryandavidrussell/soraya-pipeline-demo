# Soraya v0.4.1 Contract Stress Tests

First honest measurement of the gap between the implemented spine and the frozen v0.4.1 spec.

## What this is

Four stress cases (UP-004 through UP-007), each targeting one frozen invariant that the
current MVP cannot yet satisfy. They are designed to **fail visibly** until the corresponding
module is implemented.

|Case  |Invariant tested                |Missing module                        |
|------|--------------------------------|--------------------------------------|
|UP-004|LR(H) is pre-judgment           |ConversationState + trajectory_monitor|
|UP-005|Ledger flags are not enforcement|PolicyEnforcementPoint (Γ=block halt) |
|UP-006|Route/Disposition split         |ReviewerCapacity (H_t)                |
|UP-007|S(x) compatibility gate         |validate_support_mode                 |

## Test structure

Each case has two tests:

- `test_*_case_is_well_formed` — always passes; verifies the spec case itself is valid
- `test_*_<invariant>` — xfail (strict) until the module exists; flips to a real pass when it lands

Plus `test_zz_implementation_gap_report` which prints the current module presence map.

## Current state (run via shim, no network)

```
pass=5  xfail=4  xpass=0  fail=0
=== v0.4.1 Implementation Gap: 0/5 modules present ===
  [ ] ConversationState
  [ ] trajectory_monitor (LR)
  [ ] Gamma PEP enforcement
  [ ] ReviewerCapacity (H_t)
  [ ] S(x) compatibility gate
```

## How to use with real pytest

```
pip install pytest
pytest tests/test_unified_pipeline_contracts.py -v
```

The xfail markers use `strict=True`. When you implement a module and its capability probe
flips to True, the xfail condition becomes False — and if the test then passes, it passes
normally. If it would XPASS while still marked, strict mode flags it, forcing you to remove
the stale marker. This keeps the test file honest as modules land.

## Implementation order (after these tests exist)

1. Add minimal `ConversationState` (session-local, no persistent memory)
1. Implement `trajectory_monitor(state)` → LR(H) output contract
1. Feed LR output into pre-judgment feature merge
1. Add `Γ` disposition object
1. Make `Γ = block` halt response/tool path (PolicyEnforcementPoint)
1. Add `S_candidate / S_final` compatibility validator
1. Expand ledger to record LR, Γ, and S fallback data
1. Flip xfail tests into passing tests one at a time

## Motto

Fail visibly. Patch narrowly. Promote one invariant at a time.