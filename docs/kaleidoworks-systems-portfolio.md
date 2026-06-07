# Kaleidoworks Systems Portfolio

## Governed AI systems for agency-preserving decision support

Kaleidoworks is developing a family of governed AI systems designed around a simple principle:

**Semantic relevance is not operational authority.**

An AI system may be able to discuss an action intelligently. That does not mean it should be allowed to recommend, execute, or automate that action without the right source evidence, user context, policy boundary, and human review path.

This repository summarizes the main systems in the Kaleidoworks / Soraya architecture family and explains how they fit together.

## Core thesis

Most AI applications optimize for answer generation.

These systems focus on a different layer:

- routing before response
- authority before action
- evidence before recommendation
- human review before high-impact decisions
- audit trails before institutional deployment
- agency preservation before dependency

The goal is not to make AI more persuasive. The goal is to make AI more structurally accountable.

## Project map

| Project | Purpose | Status |
|---|---|---|
| **Soraya** | Agency-preserving AI assistant for clarification, triage, tiny-step planning, reflection, and safety-bound support | Runnable MVP |
| **C3-ICM / LRAI Router** | Governance routing layer that separates semantic relevance from operational authority | Tested research prototype |
| **Pre-HITL Evidence Packets** | Human-in-the-loop evidence packet workflow originally developed for healthcare-style review contexts | Labeling-pilot ready |
| **Soraya Scout** | Small-business opportunity-search workflow that translates trusted sources into advisor-reviewable opportunity packets | Pilot concept / domain adaptation |
| **Agency Ledger** | Logging layer for tracking whether AI support preserves or displaces user agency | Integrated in Soraya MVP |
| **Domain Packs** | Configurable source-trust, action-sensitivity, and authority rules for different operational domains | In development |

## 1. Soraya

Soraya is an agency-preserving AI assistant designed to help users clarify situations, triage overload, identify tiny next steps, and preserve judgment under pressure.

Soraya is not designed to replace the user’s decision-making. It is designed to return agency to the user.

### Current capabilities

- Clarify mode
- Triage mode
- Tiny Step mode
- Reflection mode
- Safety mode
- Routing panel
- Agency Ledger
- Session-level support tracking

### Design principle

Soraya should help the user move from confusion to a next responsible action without becoming dependent on the system’s judgment.

## 2. C3-ICM / LRAI Router

The C3-ICM / LRAI router is the governance spine of the architecture.

It evaluates whether a request should follow a fast, medium, or deep review path based on factors such as authority confusion, source trust, action sensitivity, user state, and escalation risk.

### Core idea

A response can be semantically relevant while still lacking operational authority.

The router is designed to prevent systems from treating “I can answer this” as equivalent to “I should act on this.”

### Key functions

- hard-stop detection
- authority checking
- action sensitivity scoring
- conservative fallback routing
- escalation handling
- policy-aware response constraints

## 3. Pre-HITL Evidence Packets

The Pre-HITL evidence packet system was developed as a structured review workflow.

The pipeline follows a simple pattern:

1. retrieve only authorized evidence
2. resolve the evidence into a structured packet
3. route the packet to a human reviewer
4. capture the reviewer’s decision
5. preserve the audit trail

This structure is portable beyond healthcare. It can support any workflow where AI performs reconnaissance but a human must make the judgment.

## 4. Soraya Scout

Soraya Scout applies the same governed architecture to small-business support.

The goal is to help small business advisors turn scattered public and institutional information into reviewable opportunity packets.

Example opportunity types:

- procurement opportunities
- vendor registration pathways
- supplier-readiness programs
- training resources
- certification requirements
- funding or grant opportunities where appropriate
- local business support programs

### What makes Soraya Scout different

Soraya Scout is not “AI search.”

It is governed workflow support.

It does not tell a business owner, “You qualify.” It gathers source evidence, flags uncertainty, assigns recommendation sensitivity, and lets an advisor approve, edit, reject, escalate, or assign a next action.

### Core workflow

1. Business profile is created.
2. Trusted sources are searched.
3. Opportunity evidence packet is generated.
4. Recommendation sensitivity is assigned.
5. Advisor reviews the packet.
6. Owner receives an approved next-step summary.
7. System logs decision trail and outcome.

## 5. Agency Ledger

The Agency Ledger tracks whether the system is helping the user retain agency or whether it risks displacing the user’s judgment.

This matters because helpful AI can become harmful when it silently trains users to outsource decisions they still need to own.

The ledger is intended to support:

- anti-dependency monitoring
- escalation awareness
- support-mode transparency
- institutional accountability
- longitudinal evaluation

## Architecture pattern

Across these projects, the recurring pattern is:

```text
User / Client Context
        ↓
Governance Router
        ↓
Source Authority + Action Sensitivity Check
        ↓
Evidence Packet or Support Mode
        ↓
Human Review Where Required
        ↓
Owner/User Next Step
        ↓
Audit Trail / Agency Ledger
```

## Current development priorities

- Unify Soraya, C3-ICM, and evidence packets into a single pilot-facing architecture
- Build Soraya Scout domain pack for small-business opportunity workflows
- Define source authority registry for public and institutional opportunity sources
- Implement recommendation sensitivity taxonomy
- Add advisor review actions: approve, edit, reject, escalate, assign
- Capture reviewer calibration data during pilot use
- Produce reportable governance metrics for institutional partners

## Governance metrics

The systems are intended to measure not only whether AI generated a useful output, but whether the workflow preserved accountable judgment.

Example metrics:

- source authority coverage
- routing decision accuracy
- advisor review time
- risky recommendations prevented
- false escalations
- owner next actions taken
- reviewer calibration data
- agency-preservation signals
- audit trail completeness

## Repository status

These projects are research and pilot-stage systems. Some components are runnable MVPs, while others are domain adaptations or validation prototypes.

The current emphasis is not on claiming full production readiness. The emphasis is on demonstrating a governed architecture that can be tested, reviewed, and improved through real-world pilot data.

## Boundary statement

These systems are not intended to provide legal, medical, financial, procurement, or compliance determinations without appropriate human review.

They are designed to support better judgment, not replace accountable decision-makers.

## Contact

Developed by Ryan Russell / Kaleidoworks.

For collaboration, pilot conversations, or research discussion, please reach out through the linked project channels.
