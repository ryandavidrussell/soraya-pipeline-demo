---
title: Soraya Pipeline Demo
emoji: 🛡️
colorFrom: green
colorTo: gray
sdk: gradio
sdk_version: 6.14.0
python_version: "3.10"
app_file: app.py
hf_oauth: true
pinned: false
license: apache-2.0
short_description: Agency-preserving AI governance router — research prototype
---

# Soraya v0.4.1 — Governance Pipeline Demo

A research prototype that routes a prompt through a unified AI-governance
pipeline and shows you exactly what happened at each stage: trajectory
monitoring, judgment routing, the Route/Disposition split, the support-mode
compatibility gate, and Γ policy enforcement.

## What you can try

Pick a scenario or type your own prompt. Watch the pipeline:

- **Benign lookup** → routes FAST, allowed.
- **Dependency spiral** (set a few prior turns like "just tell me what to do")
  → the trajectory monitor raises a route floor *before* judgment runs.
- **Expense bypass, action unauthorized** → Γ physically blocks the action;
  the side effect does not execute.
- **Medical / legal advice** → escalates to a professional boundary.
- **Legal advice under saturated reviewers** → disposition becomes *defer*,
  but the risk route is **not** downgraded.
- **Emotional + life decision** → stabilize first, preserve the user's agency.

## What is actually enforced

Four stages are the real, regression-locked modules from the build. They are
not illustrative mockups:

|Invariant                            |What it guarantees                                                                                                            |
|-------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
|**LR(H)** — trajectory monitor       |Runs before judgment; a cross-turn dependency spiral raises risk even when the single turn looks benign.                      |
|**H_t** — Route/Disposition split    |Reviewer saturation may change *what executes*, never *what the situation is*. The route downgrade is structurally impossible.|
|**S(x)** — support compatibility gate|"Helpful coaching" cannot become a soft bypass. Mode + frame decides validity, deny-by-default.                               |
|**Γ PEP** — enforcement              |Blocked actions are physically prevented from executing, not just logged. Fails closed.                                       |

**Reproduce it:** `pytest tests/ -v` — contract suite `pass=9 xfail=0 gap=5/5`,
plus 34 unit tests. Every green checkbox is a test that runs against real code
and fails if the code is wrong. The gap report is a measurement, not a roadmap
of intentions.

## Architecture Portfolio

For a broader overview of the Kaleidoworks / Soraya governance ecosystem — including Soraya, C3-ICM / LRAI Router, Pre-HITL Evidence Packets, Soraya Scout, the Agency Ledger, and Domain Packs — see:

[ Kaleidoworks Systems Portfolio](docs/kaleidoworks-systems-portfolio.md)

## Scope boundary (read this)

This is **not production, not enterprise-ready, and not a claim that AI
governance is solved.** The judgment router in this demo is a compact keyword
classifier — the frozen v0.8 deterministic baseline. It will miss paraphrased
intent; that is the documented ceiling of the deterministic layer. The
*enforcement* layer is the tested code.

Still out of scope: production IAM, the full agent runtime, the semantic
detector implementation, persistent memory governance, and real-world
professional decision authority.

What is proven is narrower and real: the core invariants of an agency-preserving
governance system can be made structural, testable, and enforceable.

*Part of the Kaleidoworks governance family. Core principle: semantic relevance
is not operational authority.*
